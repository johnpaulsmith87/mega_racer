from OpenGL.GL import *
import glfw

import numpy as np
from ctypes import sizeof, c_float, c_void_p, c_uint, string_at
import math
import sys
from PIL import Image
import random
import imgui

# we use 'warnings' to remove this warning that ImGui[glfw] gives
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from imgui.integrations.glfw import GlfwRenderer as ImGuiGlfwRenderer

from lab_utils import Mat3, Mat4, make_translation, normalize

from ObjModel import ObjModel
import lab_utils as lu
from lab_utils import vec3, vec2

g_shadowWidth = 1024
g_shadowHeight = 1024
TU_depthTexture = 9
TU_depthTexture2 = 10 #??
vertexArrayObject = None
def setupShadowMap(terrain):
    depthTexture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, depthTexture)
    glTexImage2D(GL_TEXTURE_2D, 0,GL_DEPTH_COMPONENT, g_shadowWidth, g_shadowHeight, 0,GL_DEPTH_COMPONENT, GL_FLOAT, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,depthTexture,0)
    glDrawBuffer(GL_NONE)
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
        return False
    return depthTexture, fbo # not sure if I need to return these!
def shadowVertShader():
    shader = """
                #version 330 core
                layout(location = 0) in vec3 vertexPosition_modelSpace;
                uniform mat4 lightPOVTransform;

                void main(){
                //actually world space but eh
                    gl_Position = lightPOVTransform * vec4(vertexPosition_modelSpace, 1.0);
                }
             """
    return shader

def shadowFragShader():
    shader = """
                #version 330 core
                layout(location = 0) out float fragmentDepth;
                
                void main(){
                    fragmentDepth = gl_FragCoord.z;
                }
             """
    return shader
#builds shadow shader
def buildShadowShader():   
    return lu.buildShader(shadowVertShader(), shadowFragShader(), ObjModel.getDefaultAttributeBindings())

def shadowRenderPass(shadowShader, view, renderingSystem, shadowTex, terrain, fbo):
    
    glViewport(0,0,g_shadowWidth,g_shadowHeight)
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, fbo)
    glClearDepth(1.0)
    glClear(GL_DEPTH_BUFFER_BIT)
    glUseProgram(shadowShader)
    renderingSystem.setCommonUniforms(shadowShader,view,lu.Mat4())
    #set common unforms?
    #bind terrain vertex array! -> we need terrain scene geometry...
    #bindTextures?
    lu.bindTexture(TU_depthTexture, shadowTex)
    lu.setUniform(shadowShader,"lightPOVTransform", view.depthMVPTransform)
    glBindVertexArray(terrain.vertexArrayObject)
    glDrawElements(GL_TRIANGLES, len(terrain.terrainInds), GL_UNSIGNED_INT, None);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0)
    glBindVertexArray(0)
    glUseProgram(0)

    