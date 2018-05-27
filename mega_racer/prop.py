from OpenGL.GL import *
import glfw
import numpy as np
import math
from PIL import Image
import imgui
import random
from enum import IntEnum

import lab_utils as lu
from lab_utils import vec3, vec2
from terrain import TerrainInfo
from ObjModel import ObjModel

class PropType(IntEnum):
    NONE = 0
    PALMTREE = 1
    GUMTREE = 2
    BIRCHTREE = 3
    TREEONE = 4
    ROCKONE = 5
    ROCKTWO = 6
    ROCKTHREE = 7
    ROCKFOUR = 8
    ROCKFIVE = 9

class Prop:
    position = vec3(0,0,0) # start at 0,0,0 to make x-axis world rot easier
    facing =  vec3(1,0,0) #world space "heading"
    rotAmount = 0.0 #how much to rotate by
    model = None #model to use
    terrain = None #not sure if I need this
    propType = 0 # propType will be used for prop specific scaling/etc
    def render(self, view, renderingSystem):
        #put switch statement here for each type of prop if ann where appropriate

        modelToWorldTransform = lu.make_mat4_from_zAxis(self.position, self.facing, vec3(0,0,1))
        rotationByRandAmount = lu.make_rotation_z(self.rotAmount)
        renderingSystem.drawObjModel(self.model,rotationByRandAmount * modelToWorldTransform, view)
    def load(self, model, terrain, renderingSytem, position):
        self.model = model[0]
        self.propType = model[1]
        self.rotAmount = random.uniform(0.001, 6.28319) # ~0 to ~360
        self.terrain = terrain
        info = self.terrain.getInfoAt(position)
        # need to set position height to terrain height
        self.position = vec3(position[0],position[1],info.height)

class PropManager:
    trees = []
    rocks = []
    terrain = None
    #list of tuples to send proptype info
    typeToFileNameList = {"rock":[("data/rocks/rock_01.obj",PropType.ROCKONE)],
                          "tree":[("data/trees/birch_01_d.obj",PropType.BIRCHTREE),
                                  ("data/trees/tree_01.obj",PropType.TREEONE)]}
    def __init__(self, terrain):
        #loads each type of prop and stores in trees and rocks
        self.terrain = terrain
        for f in self.typeToFileNameList["rock"]:
            self.rocks.append((ObjModel(f[0]),f[1]))
        for f in self.typeToFileNameList["tree"]:
            self.trees.append((ObjModel(f[0]),f[1]))
    def createTreeProp(self,terrain, renderingSystem, position):
        newProp = Prop()
        numTrees = len(self.trees)
        treeInd = random.randint(0, numTrees - 1)
        newProp.load(self.trees[treeInd],terrain, renderingSystem, position)
        return newProp
    def createRockProp(self,terrain, renderingSystem, position):
        newProp = Prop()
        numRocks = len(self.rocks)
        rockInd = random.randint(0, numRocks - 1)
        newProp.load(self.rocks[rockInd],terrain, renderingSystem, position)
        return newProp


