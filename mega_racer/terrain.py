from OpenGL.GL import *
import glfw
import numpy as np
import math
from PIL import Image
import imgui
import shadow
import lab_utils as lu
from lab_utils import vec3, vec2
from ObjModel import ObjModel

# returned by getInfoAt to provide easy access to height and material type on the terrain for use
# by the game logic.
class TerrainInfo:
    M_Road = 0 
    M_Rough = 1
    height = 0.0
    material = 0


# This class looks after loading & generating the terrain geometry as well as rendering.
# It also provides access to the terrain height and type at different points.
class Terrain:
    xyScale = 8.0
    heightScale = 75.0
    textureXyScale = 0.1

    imageWidth = 0
    imageHeight = 0
    shader = None
    renderWireFrame = False
    terrainTexId = None #grass
    highTexId = None #high texture
    roadTexId = None
    steepTexId = None
    terrainDataSampleTexId = None
    #specular textures
    specGrassTexId = None
    specHighTexId = None
    specRoadTexId = None
    specSteepTexId = None

    # Lists of locations generated from the map texture green channel (see the 'load' method)
    # you can add any other meaning of other values as you see fit.
    
    # Locations to place racers at (the start-grid if you will)
    startLocations = []
    # Locations where trees might be put down (the demo implementation samples these randomly)
    treeLocations = []
    # Same for rocks
    rockLocations = []

    # Texture unit allocaitons:
    TU_Grass = 0
    TU_high = 1
    TU_road = 2
    TU_steep = 3
    TU_map = 4
    TU_spec_grass = 5
    TU_spec_high = 6
    TU_spec_steep = 7
    TU_spec_road = 8
    
    def render(self, view, renderingSystem, depthMap):
        glUseProgram(self.shader)
        renderingSystem.setCommonUniforms(self.shader, view, lu.Mat4())

        lu.setUniform(self.shader, "terrainHeightScale", self.heightScale);
        lu.setUniform(self.shader, "terrainTextureXyScale", self.textureXyScale);
        xyNormScale = 1.0 / (vec2(self.imageWidth, self.imageHeight) * self.xyScale);
        lu.setUniform(self.shader, "xyNormScale", xyNormScale);
        xyOffset = -(vec2(self.imageWidth, self.imageHeight) + vec2(1.0)) / 2.0
        lu.setUniform(self.shader, "xyOffset", xyOffset);
        lu.setUniform(self.shader,"depthMVPTransform", view.depthMVPTransform)
        #depthTexture binding for use in terrain frag shader
        lu.bindTexture(shadow.TU_depthTexture, depthMap)
        lu.setUniform(self.shader, "shadowMapTexture", shadow.TU_depthTexture)
         #FINISH HERE
        #TODO 1.4: Bind the grass texture to the right texture unit, hint: lu.bindTexture
        lu.bindTexture(self.TU_Grass, self.terrainTexId)
        lu.bindTexture(self.TU_high, self.highTexId)
        lu.bindTexture(self.TU_road, self.roadTexId)
        lu.bindTexture(self.TU_steep, self.steepTexId)
        lu.bindTexture(self.TU_map, self.terrainDataSampleTexId)
        #bind specs
        lu.bindTexture(self.TU_spec_grass, self.specGrassTexId)
        lu.bindTexture(self.TU_spec_high, self.specHighTexId)
        lu.bindTexture(self.TU_spec_road, self.specRoadTexId)
        lu.bindTexture(self.TU_spec_steep, self.specSteepTexId)
        #set uniform specs
        lu.setUniform(self.shader, "specularGrassTexture", self.TU_spec_grass)
        lu.setUniform(self.shader, "specularHighTexture", self.TU_spec_high)
        lu.setUniform(self.shader, "specularRoadTexture", self.TU_spec_road)
        lu.setUniform(self.shader, "specularSteepTexture", self.TU_spec_steep)
        #
        lu.setUniform(self.shader, "terrainTexture", self.TU_Grass)
        lu.setUniform(self.shader, "highTexture", self.TU_high)
        lu.setUniform(self.shader, "roadTexture", self.TU_road)
        lu.setUniform(self.shader, "steepTexture", self.TU_steep)
        lu.setUniform(self.shader, "terrainDataSample", self.TU_map)

        if self.renderWireFrame:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
            glLineWidth(1.0);
        glBindVertexArray(self.vertexArrayObject);
        glDrawElements(GL_TRIANGLES, len(self.terrainInds), GL_UNSIGNED_INT, None);

        if self.renderWireFrame:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);
        glBindVertexArray(0);
        glUseProgram(0);


    def load(self, imageName, renderingSystem):
        
        with Image.open(imageName)  as im:
            self.imageWidth = im.size[0]
            self.imageHeight = im.size[1]
            self.imageData = im.tobytes("raw", "RGBX" if im.mode == 'RGB' else "RGBA", 0, -1)

            xyOffset = -vec2(float(self.imageWidth), float(self.imageHeight)) * self.xyScale / 2.0;

            # Calculate vertex positions
            terrainVerts = []
            for j in range(self.imageHeight):
                for i in range(self.imageWidth):
                    offset = (j * self.imageWidth + i) * 4
                    # copy pixel 4 channels
                    imagePixel = self.imageData[offset:offset+4];
                    # Normalize the red channel from [0,255] to [0.0, 1.0]
                    red = float(imagePixel[0]) / 255.0;

                    xyPos = vec2(i, j) * self.xyScale + xyOffset;
                    # TODO 1.1: set the height
                    zPos = self.heightScale*red
                    pt = vec3(xyPos[0], xyPos[1], zPos)
                    terrainVerts.append(pt)

                    green = imagePixel[1];
                    if green == 255:
                        self.startLocations.append(pt)
                    if green == 128:
                        self.treeLocations.append(pt)
                    if green == 64:
                        self.rockLocations.append(pt)

            # build vertex normals...
            terrainNormals = [vec3(0.0, 0.0, 1.0)] * self.imageWidth * self.imageHeight;
            for j in range(1, self.imageHeight - 1):
                for i in range(1, self.imageWidth - 1):
                    v = terrainVerts[j * self.imageWidth + i];
                    vxP = terrainVerts[j * self.imageWidth + i - 1];
                    vxN = terrainVerts[j * self.imageWidth + i + 1];
                    dx = vxP - vxN;

                    vyP = terrainVerts[(j - 1) * self.imageWidth + i];
                    vyN = terrainVerts[(j + 1) * self.imageWidth + i];
                    dy = vyP - vyN;

                    nP = lu.normalize(lu.cross(dx, dy));

                    vdxyP = terrainVerts[(j - 1) * self.imageWidth + i - 1];
                    vdxyN = terrainVerts[(j + 1) * self.imageWidth + i + 1];
                    dxy = vdxyP - vdxyN;

                    vdyxP = terrainVerts[(j - 1) * self.imageWidth + i + 1];
                    vdyxN = terrainVerts[(j + 1) * self.imageWidth + i - 1];
                    dyx = vdyxP - vdyxN;

                    nD = lu.normalize(lu.cross(dxy, dyx));

                    terrainNormals[j * self.imageWidth + i] = lu.normalize(nP + nD);



            # join verts with quads that is: 2 triangles @ 3 vertices, with one less in each direction.
            terrainInds = [0] * 2 * 3 * (self.imageWidth - 1) * (self.imageHeight - 1)
            for j in range(0, self.imageHeight - 1):
                for i in range(0, self.imageWidth - 1):
				    # Vertex indices to the four corners of the quad.
                    qInds =[
					    j * self.imageWidth + i,
					    j * self.imageWidth + i + 1,
					    (j + 1) * self.imageWidth + i,
					    (j + 1) * self.imageWidth + i + 1,
				    ]
                    outOffset = 3 * 2 * (j * (self.imageWidth - 1) + i);
                    points = [
					    terrainVerts[qInds[0]],
					    terrainVerts[qInds[1]],
					    terrainVerts[qInds[2]],
					    terrainVerts[qInds[3]],
                    ]
                    # output first triangle:
                    terrainInds[outOffset + 0] = qInds[0];
                    terrainInds[outOffset + 1] = qInds[1];
                    terrainInds[outOffset + 2] = qInds[2];
                    # second triangle
                    terrainInds[outOffset + 3] = qInds[2];
                    terrainInds[outOffset + 4] = qInds[1];
                    terrainInds[outOffset + 5] = qInds[3];
            
            self.terrainInds = terrainInds

            self.vertexArrayObject = lu.createVertexArrayObject();
            self.vertexDataBuffer = lu.createAndAddVertexArrayData(self.vertexArrayObject, terrainVerts, 0);
            self.normalDataBuffer = lu.createAndAddVertexArrayData(self.vertexArrayObject, terrainNormals, 1);
            self.indexDataBuffer = lu.createAndAddIndexArray(self.vertexArrayObject, terrainInds);

            #normalDataBuffer = createAndAddVertexArrayData<vec4>(g_particleVao, { vec4(0.0f) }, 1);



        vertexShader = """
            #version 330
            in vec3 positionIn;
            in vec3 normalIn;

            uniform mat4 worldToViewTransform;
            uniform mat4 modelToClipTransform;
            uniform mat4 modelToViewTransform;
            uniform mat3 modelToViewNormalTransform;
            uniform mat4 depthMVPTransform;
            
            uniform sampler2D terrainDataSampler;
            uniform float terrainHeightScale;
            uniform float terrainTextureXyScale;
            uniform vec2 xyNormScale;
            uniform vec2 xyOffset;
            

            // 'out' variables declared in a vertex shader can be accessed in the subsequent stages.
            // For a fragment shader the variable is interpolated (the type of interpolation can be modified, try placing 'flat' in front here and in the fragment shader!).
            out VertexData
            {
	            float v2f_height;
                vec3 v2f_viewSpacePosition;
                vec3 v2f_viewSpaceNormal;
                vec3 v2f_worldSpacePosition;
                vec2 normalizedXYcoords;
                float distance;
                vec3 viewToVertexPosition;
                vec3 worldSpaceNormal;
                vec4 fragPosLightSpace;
            };

            void main() 
            {
                // pass the world-space Z to the fragment shader, as it is used to compute the colour and other things
	            v2f_height = positionIn.z;
                v2f_worldSpacePosition = positionIn;
                v2f_viewSpacePosition = (modelToViewTransform * vec4(positionIn, 1.0)).xyz;
                v2f_viewSpaceNormal = modelToViewNormalTransform * normalIn;
                worldSpaceNormal = normalIn;
                normalizedXYcoords = positionIn.xy * xyNormScale + xyOffset;
                distance = -v2f_viewSpacePosition.z;
                //first use the worldToViewTransform to get the camera world space coords
                vec3 cameraPosInWorldSpace = vec3(worldToViewTransform[3][0],worldToViewTransform[3][1],worldToViewTransform[3][2]);
                viewToVertexPosition = normalize(positionIn - cameraPosInWorldSpace);
	            // gl_Position is a buit-in 'out'-variable that gets passed on to the clipping and rasterization stages (hardware fixed function).
                // it must be written by the vertex shader in order to produce any drawn geometry. 
                // We transform the position using one matrix multiply from model to clip space. Note the added 1 at the end of the position to make the 3D
                // coordinate homogeneous.
                fragPosLightSpace = depthMVPTransform * vec4(positionIn, 1.0);
	            gl_Position = modelToClipTransform * vec4(positionIn, 1.0);
            }
"""

        fragmentShader = """
            // Input from the vertex shader, will contain the interpolated (i.e., area weighted average) vaule out put for each of the three vertex shaders that 
            // produced the vertex data for the triangle this fragmet is part of.
            in VertexData
            {
	            float v2f_height;
                vec3 v2f_viewSpacePosition;
                vec3 v2f_viewSpaceNormal;
                vec3 v2f_worldSpacePosition;
                vec2 normalizedXYcoords;
                float distance; //camera to geometry distance
                vec3 viewToVertexPosition;
                vec3 worldSpaceNormal;
                vec4 fragPosLightSpace;
            };

            uniform float terrainHeightScale;
            uniform float terrainTextureXyScale;
            uniform sampler2D terrainTexture;
            uniform sampler2D roadTexture;
            uniform sampler2D highTexture;
            uniform sampler2D steepTexture;
            uniform sampler2D terrainDataSample;
            //
            uniform sampler2D specularGrassTexture;
            uniform sampler2D specularHighTexture;
            uniform sampler2D specularRoadTexture;
            uniform sampler2D specularSteepTexture;
            //
            uniform sampler2D shadowMapTexture;
            out vec4 fragmentColor;

            void main() 
            {
                // trying height = 0.7 / steep 0.5
                //vec3 materialColour = vec3(v2f_height/terrainHeightScale);
                // TODO 1.4: Compute the texture coordinates and sample the texture for the grass and use as material colour.
                vec3 materialDiffuse;
                vec3 materialSpecular;
                float steepThreshold = 0.959931; //roughly 55 degrees rad
                float steepness = acos(dot(normalize(worldSpaceNormal), vec3(0,0,1)));
                vec3 blueChannel = texture(terrainDataSample, normalizedXYcoords).xyz;
                float matSpecExp;
                vec3 reflectedLight;

                if(blueChannel.b == 1.0)
                {
                    materialDiffuse = texture(roadTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    materialSpecular = texture(specularRoadTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    reflectedLight = computeShadingDiffuse(materialDiffuse, v2f_viewSpacePosition, v2f_viewSpaceNormal, viewSpaceLightPosition, sunLightColour, fragPosLightSpace, shadowMapTexture);
                }
                else if(steepness > steepThreshold)
                {
                    materialDiffuse = texture(steepTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    materialSpecular = texture(specularSteepTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    reflectedLight = computeShadingDiffuse(materialDiffuse, v2f_viewSpacePosition, v2f_viewSpaceNormal, viewSpaceLightPosition, sunLightColour, fragPosLightSpace, shadowMapTexture);
                }
                else if (v2f_height > 55)
                {
                    materialDiffuse = texture(highTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    materialSpecular = texture(specularHighTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    matSpecExp = 50.0;
                    reflectedLight = computeShadingSpecular(materialDiffuse, materialSpecular, v2f_viewSpacePosition, v2f_viewSpaceNormal, viewSpaceLightPosition, sunLightColour, matSpecExp,  fragPosLightSpace, shadowMapTexture);
                }
                else
                {
                    materialDiffuse = texture(terrainTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    materialSpecular = texture(specularGrassTexture, vec2(v2f_worldSpacePosition.x,v2f_worldSpacePosition.y) * terrainTextureXyScale).xyz;
                    matSpecExp = 150.0;
                    reflectedLight = computeShadingSpecular(materialDiffuse, materialSpecular, v2f_viewSpacePosition, v2f_viewSpaceNormal, viewSpaceLightPosition, sunLightColour, matSpecExp,  fragPosLightSpace, shadowMapTexture);
                }
                
	            fragmentColor = vec4(toSrgb(applyFog(reflectedLight,distance, v2f_viewSpacePosition, viewToVertexPosition)), 1.0);
	            //fragmentColor = vec4(toSrgb(vec3(v2f_height/terrainHeightScale)), 1.0);

            }
"""
        # Note how we provide lists of source code strings for the two shader stages.
        # This is basically the only standard way to 'include' or 'import' code into more than one shader. The variable renderingSystem.commonFragmentShaderCode
        # contains code that we wish to use in all the fragment shaders, for example code to transform the colour output to srgb.
        # It is also a nice place to put code to compute lighting and other effects that should be the same accross the terrain and racer for example.
        self.shader = lu.buildShader([vertexShader], ["#version 330\n", renderingSystem.commonFragmentShaderCode, fragmentShader], {"positionIn" : 0, "normalIn" : 1})
        
        # TODO 1.4: Load texture and configure the sampler
        self.terrainTexId = ObjModel.loadTexture("data/grass2.png","", True)
        self.highTexId = ObjModel.loadTexture("data/rock 2.png","",True)
        self.roadTexId = ObjModel.loadTexture("data/paving 5.png","", True)
        self.steepTexId = ObjModel.loadTexture("data/rock 5.png","", True)
        self.specGrassTexId = ObjModel.loadTexture("data/grass_specular.png","", True)
        self.specHighTexId = ObjModel.loadTexture("data/high_specular.png","", True)
        self.specSteepTexId = ObjModel.loadTexture("data/steep_specular.png","", True)
        self.specRoadTexId = ObjModel.loadTexture("data/road_specular.png","", True)
        self.terrainDataSampleTexId = ObjModel.loadTexture("data/track_01_128.png","", False)
    # Called by the game to drawt he UI widgets for the terrain.
    def drawUi(self):
        # height scale is read-only as it is not run-time changable (since we use it to compute normals at load-time)
        imgui.label_text("terrainHeightScale", "%0.2f"%self.heightScale)
        #_,self.heightScale = imgui.slider_float("terrainHeightScale", self.heightScale, 1.0, 100.0)
        _,self.textureXyScale = imgui.slider_float("terrainTextureXyScale", self.textureXyScale, 0.01, 10.0)
        _,self.renderWireFrame = imgui.checkbox("WireFrame", self.renderWireFrame);


    # Retrieves information about the terrain at some x/y world-space position, if you request info from outside 
    # the track it just clamps the position to the edge of the track.
    # Returns an instance of the class TerrainInfo.
    # An improvement that would make the movement of the racer smoother is to bi-linearly interpolate the image data.
    # this is something that comes free with OpenGL texture sampling, but here we'd have to implement it ourselves.
    def getInfoAt(self, position):
        # 1. convert x&y to texture scale
        xyOffset = -vec2(self.imageWidth, self.imageHeight) * self.xyScale / 2.0
        imageSpacePos = (vec2(position[0], position[1]) - xyOffset) / self.xyScale;

        x = max(0, min(self.imageWidth - 1, int(imageSpacePos[0])))
        y = max(0, min(self.imageHeight - 1, int(imageSpacePos[1])))
        pixelOffset = (y * self.imageWidth + x) * 4
        # copy pixel 4 channels
        imagePixel = self.imageData[pixelOffset:pixelOffset+4]

        info = TerrainInfo();
        info.height = float(imagePixel[0]) * self.heightScale / 255.0;
        info.material = TerrainInfo.M_Road if imagePixel[2] == 255 else TerrainInfo.M_Rough
        return info;

def load_terrain_texture(textureFile):
    with Image.open(textureFile) as image:
        texId = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texId)
        data = image.tobytes("raw", "RGBX" if image.mode == 'RGB' else "RGBA", 0, -1)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image.size[0],image.size[1],0,GL_RGBA,
                     GL_UNSIGNED_BYTE,data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)
        return texId