#Author: Claudio Pedica
#Date: 21/11/2011
#
# A modified version of Tut-Cartoon-Advanced.py that uses the
# Cartoon Painter class. Cartoon Painter can selectively apply
# toon shading and inking only to a designated set of nodepaths.
# The Cartoon Painter allows to change the step function for the
# toon shading to get different or multiple levels of brightness.

import sys
import os
import math
import direct.directbase.DirectStart
from direct.showbase.DirectObject import DirectObject
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
from panda3d.core import Vec3
from panda3d.core import Point3
from panda3d.core import TextNode
from cartoonpainter.cartoonpainter import CartoonPainter

# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1),
                        pos=(-1.3, pos), align=TextNode.ALeft, scale=.05)

# Function to put title on the screen.
def addTitle(text):
    return OnscreenText(text=text, style=1, fg=(1, 1, 1, 1),
                        pos=(1.3, -0.95), align=TextNode.ARight, scale=.07)


class ToonMaker(DirectObject):
    
    def __init__(self):
        self._spotlight_effect = False
        self._step_funcs = [(0.8, 1.0, 1.0), (0.6, 1.0, 3.0),
                            (0.7, 1.0, 8.0), (0.75, 1.0, 16.0)]
        self._cur = 0
        
        # Create the cartoon painter. It will automatically initialize 
        # all the display regions, scenes and cameras to achieve necessary
        # for the cartoonish effect.
        
        self.cartoon_painter = CartoonPainter()
        
        base.setFrameRateMeter(True)
        self.title = addTitle("A mod of Tut-Cartoon-Advanced show casing selective cartoon painting.")
        self.inst1 = addInstructions(0.95, "ESC: Quit")
        self.inst2 = addInstructions(0.90, "Up/Down: Increase/Decrease Line Thickness")
        self.inst3 = addInstructions(0.85, "Left/Right: Decrease/Increase Line Darkness")
        self.inst4 = addInstructions(0.80, "c: Toggle camera spot light effect.")
        self.inst5 = addInstructions(0.75, "x: Change step function.")
        self.inst6 = addInstructions(0.70, "v: View the render-to-texture results")
        
        # Panda contains a built-in viewer that lets you view the results of
        # your render-to-texture operations.  This code configures the viewer.
        
        self.accept("v", base.bufferViewer.toggleEnable)
        base.bufferViewer.setPosition("llcorner")
        
        # These allow you to change the cartoon painter parameters
        # in realtime.
        
        self.accept("escape", sys.exit, [0])
        self.accept("arrow_up", self.increaseSeparation)
        self.accept("arrow_down", self.decreaseSeparation)
        self.accept("arrow_left", self.increaseCutoff)
        self.accept("arrow_right", self.decreaseCutoff)
        self.accept('c', self.toggleCameraSpotLigth)
        self.accept('x', self.switchStepFunc)
        self.accept('f12', base.screenshot)

        # Load some dragon models and animate them. We want a big dragon
        # in the middle and many more little dragons all around.
        
        big_nik = Actor()
        big_nik.loadModel('nik-dragon')
        big_nik.reparentTo(render)
        big_nik.setPos(0, 70, 0)
        big_nik.loadAnims({'win': 'nik-dragon'})
        big_nik.loop('win')
        big_nik.hprInterval(15, Point3(360, 0, 0)).loop()
        
        BABY_NIKS = 8
        RADIUS = 20.0
        self.babies = []
        for i in xrange(BABY_NIKS + 1):
            theta = 2.0 * math.pi * i / BABY_NIKS
            x = math.cos(theta)
            y = math.sin(theta)
            pos = big_nik.getPos() + Vec3(x, y, -0.3) * RADIUS
            baby_nik = Actor()
            baby_nik.loadModel('nik-dragon')
            baby_nik.reparentTo(render)
            baby_nik.setPos(pos)
            baby_nik.setScale(0.3)
            baby_nik.loadAnims({'win': 'nik-dragon'})
            baby_nik.loop('win')
            baby_nik.hprInterval(5, Point3(360, 0, 0)).loop()
            self.babies.append(baby_nik)
        
        # Of all the dragons, we want only big nik to be cartoon shaded.
        # To achieve this effect, it's enough to ask the cartoon painter
        # to paint just big nik.
        
        self.cartoon_painter.paint(big_nik)
        
    def increaseSeparation(self):
        self.cartoon_painter.separation *= 1.11111111;
        print self.cartoon_painter.separation
        
    def decreaseSeparation(self):
        self.cartoon_painter.separation *= 0.90000000;
        print self.cartoon_painter.separation
        
    def increaseCutoff(self):
        self.cartoon_painter.cutoff *= 1.11111111;
        print self.cartoon_painter.cutoff
        
    def decreaseCutoff(self):
        self.cartoon_painter.cutoff *= 0.90000000;
        print self.cartoon_painter.cutoff

    def toggleCameraSpotLigth(self):
        self._spotlight_effect = not self._spotlight_effect
        self.cartoon_painter.camera_spot_light(self._spotlight_effect)
    
    def switchStepFunc(self):
        self._cur = (self._cur + 1) % len(self._step_funcs)
        self.cartoon_painter.set_step_func(*self._step_funcs[self._cur])
        
t = ToonMaker()
run()

