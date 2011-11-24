
import sys

from panda3d.core import Camera
from panda3d.core import NodePath
from panda3d.core import Vec4

class CartoonPainter(object):
    """Paint just a specific nodepath whit cartoon shading and inking. This is
    good for creating interesting scene where only few objects look cartoonized.
    
    To achieve the effect, this class creates two extra display regions where
    the cartoonized nodepaths are drawn into. These regions are connected to
    two scenes called toon_render (for objects with toon shading) and 
    inking_render2d (for the objects black outlines).
    
    These regions has to be drawn before the main scene in render. You can
    adjust the sorting by setting the parameter in the constructor. The sort
    parameter is the sort value for the region of inking_render2d; the region
    of toon_render comes right after (sort - 1).
    
    You can cartoon paint a model even when it's deeply nested into any nodes
    hierarchy of your main scene. When you paint a nodepath you actually create
    an instance under toon_render. The original nodepath will be stashed but
    still retain its parents hierarchy under render and therefore its global
    transform. The CartoonPainter will take care of synchronizing position and
    rotation of the instances under toon_render.
    
    Limitations:
      * Cartoon shading doesn't not apply to transparent models.
      * Cartoon shading doesn't not apply to textured models. It works only
        for vertex and flat colored models.
      * Ink outlines are not affected by fog.
    
    Bugs:
      * A glgsg error is printed out when you exit your Panda script:
        (glGraphicsBuffer_src.cxx, line 1020: GL error 1282). Perhaps the
        normals buffer has to be destroyed before exiting?
      * On my old machine with Intel integrated graphics card the CartoonPainter
        crashes my Panda script.
    """
    
    DEFAULT_STEPFUNC_MIN = 0.8
    DEFAULT_STEPFUNC_MAX = 1.0
    DEFAULT_STEPFUNC_STEPS = 1.0
    DEFAULT_SEPARATION = 0.001
    DEFAULT_CUTOFF = 0.3
    DEFAULT_LIGHT_POS = (30, -50, 0)
    CARTOON_SHADING_SHADER = 'cartoonpainter/shading.sha'
    CARTOON_NORMALS_SHADER = 'cartoonpainter/normalGen.sha'
    CARTOON_INKING_SHADER = 'cartoonpainter/inkGen.sha'
    CARTOON_SHADING_TAG = 'CartoonPainter.CartoonShading'
    CARTOON_INKING_TAG = 'CartoonPainter.CartoonInking'
    
    def __init__(self, sort=-1):
        """Set a sort value or the two extra display regions created by the
        CartoonPainter.
        """

        self._enabled = True
        self._camera_spot_light = False
        self._paintings = {}
        self._stepf_min = self.DEFAULT_STEPFUNC_MIN
        self._stepf_max = self.DEFAULT_STEPFUNC_MAX
        self._stepf_steps = self.DEFAULT_STEPFUNC_STEPS
        self._separation = self.DEFAULT_SEPARATION
        self._cutoff = self.DEFAULT_CUTOFF
        
        # Check if the video card supports shaders. If it doesn't then the
        # CartoonPainter will be disabled.
        
        self._shaders_supported = base.win.getGsg().getSupportsBasicShaders()
        if not self._shaders_supported:
            self._enabled = False
            sys.stderr.write("CartoonPainter disabled. Video driver " +
                             "reports that shaders are not supported.")
            return
        
        # Create two new scenes, one 3d and the other 2d. The 3d scene will
        # have attached all those nodepaths we want to cartoon paint. The
        # 2d scene will have a card where the black outlines of the cartoon
        # inking are drawn. 
         
        self.toon_render = NodePath('toon_render')
        self.inking_render2d = NodePath('inking_render2d')
        self.inking_render2d.setDepthTest(False)
        self.inking_render2d.setDepthWrite(False)        
                
        # Make a new display region where to render objects in cartoon shading.
        # toon_render will have a light node used by the shader as input.
        
        self._toon_dr = base.win.makeDisplayRegion()
        self._toon_dr.setSort(sort-1)
        self._toon_camera = self.toon_render.attachNewNode(Camera('toon_camera'))
        self._toon_camera.node().setLens(base.cam.node().getLens())
        self._toon_dr.setCamera(self._toon_camera)
        self._light = self.toon_render.attachNewNode('light')
        self._light.setPos(*self.DEFAULT_LIGHT_POS)
        self.toon_render.setShaderInput('light', self._light)
        self.toon_render.setShaderInput('min', Vec4(self._stepf_min))
        self.toon_render.setShaderInput('max', Vec4(self._stepf_max))
        self.toon_render.setShaderInput('steps', Vec4(self._stepf_steps))
        _tmp = NodePath('_tmp')
        _tmp.setShader(loader.loadShader(self.CARTOON_SHADING_SHADER))
        self._toon_camera.node().setTagStateKey(self.CARTOON_SHADING_TAG)
        self._toon_camera.node().setTagState('True', _tmp.getState())        
        
        # Make a 'normals buffer' used later by the cartoon inker to get the
        # black outlines around all the objects of toon_render. The normals
        # buffer will contain a picture of the model colorized so that the
        # color of the model is a representation of the model's normal at that
        # point.
        
        self._normals_buf = base.win.makeTextureBuffer('normals_buf', 0, 0)
        self._normals_buf.setClearColor(Vec4(0.5, 0.5, 0.5, 1))
        self._normals_camera = base.makeCamera(self._normals_buf,
                                               camName='normals_camera',
                                               lens=base.cam.node().getLens())
        self._normals_camera.reparentTo(self.toon_render)
        _tmp = NodePath('_tmp')
        _tmp.setShader(loader.loadShader(self.CARTOON_NORMALS_SHADER))
        self._normals_camera.node().setInitialState(_tmp.getState())
        
        # Make a new display region for a 2d scene where we are going to draw
        # a texture card with the black outlines of every objects in
        # toon_render.
        
        self._inking_dr = base.win.makeDisplayRegion()
        self._inking_dr.setSort(sort)
        self._inking_camera = self.inking_render2d.attachNewNode(Camera('inking_camera'))
        self._inking_camera.node().setLens(base.cam2d.node().getLens())
        self._inking_dr.setCamera(self._inking_camera)

        # Extract a texture card from the normal buffer and process it using
        # the cartoon inker. The final result will be a transparent texture
        # containing the black outlines for every objects in toon_render. 

        self._ink_outlines = self._normals_buf.getTextureCard()
        self._ink_outlines.setTransparency(1)
        self._ink_outlines.setColor(1, 1, 1, 0)
        self._ink_outlines.reparentTo(self.inking_render2d)
        self._ink_outlines.setShader(loader.loadShader(self.CARTOON_INKING_SHADER))
        self._ink_outlines.setShaderInput("separation",
                                          Vec4(self._separation, 0,
                                               self._separation, 0))
        self._ink_outlines.setShaderInput("cutoff", Vec4(self._cutoff))
        
        # Start a task to update the internal cameras and every nodepath in
        # toon_render.
        
        taskMgr.add(self._update, '%s.update' % self.__class__.__name__)

    def _update(self, task):
        if self._enabled:
            cam_quat = base.camera.getQuat(base.camera.getTop())
            cam_pos = base.camera.getPos(base.camera.getTop())
            cam_lens = base.cam.node().getLens()
            self._toon_camera.setQuat(self._toon_camera.getTop(), cam_quat)
            self._toon_camera.setPos(self._toon_camera.getTop(), cam_pos)
            self._normals_camera.setQuat(self._normals_camera.getTop(),cam_quat)
            self._normals_camera.setPos(self._normals_camera.getTop(), cam_pos)
            self._toon_camera.node().setLens(cam_lens)
            self._normals_camera.node().setLens(cam_lens)
            if self._camera_spot_light: self.set_light_pos(*cam_pos)
            for np in self._paintings:
                # We re-synch position and rotation of the painted instances
                # with their corresponding original nodepaths. We grab the parent
                # transform here because an instance takes the nodepath local
                # transform when instancing from it.
                
                _inp = self._paintings[np]
                _inp.setQuat(_inp.getTop(), np.getParent().getQuat(np.getTop()))
                _inp.setPos(_inp.getTop(), np.getParent().getPos(np.getTop()))
        
        return task.cont
    
    def get_separation(self):
        return self._separation

    def get_cutoff(self):
        return self._cutoff

    def set_separation(self, x):
        if self._enabled:
            self._separation = x
            self._ink_outlines.setShaderInput('separation', Vec4(x, 0, x, 0))
    
    def set_cutoff(self, x):
        if self._enabled:
            self._cutoff = x
            self._ink_outlines.setShaderInput('cutoff', Vec4(x))
    
    def set_light_pos(self, x, y, z):
        """Set the light position used by the cartoon shading."""
        if self._enabled:
            self._light.setPos(x , y, z)
            self.toon_render.setShaderInput('light', self._light)
    
    def set_step_func(self, min, max, steps):
        """Set the step function used by the cartoon shading. Set by choosing
        min and max brightness and number of steps."""
        if self._enabled:
            # Check input format.
            min = min if min > 0.0 else 0.0
            max = max if max > 0.0 else 0.0
            steps = steps if steps > 0.0 else 0.0
            if min > max: min = max
            
            self._stepf_min = min 
            self._stepf_max = max
            self._stepf_steps = steps
            self.toon_render.setShaderInput('min', Vec4(self._stepf_min))
            self.toon_render.setShaderInput('max', Vec4(self._stepf_max))
            self.toon_render.setShaderInput('steps', Vec4(self._stepf_steps))

    def enable(self):
        """Enable the cartoon painter."""
        if self._shaders_supported:
            self._enabled = True
    
    def disable(self):
        """Disable the cartoon painter. It will not undo nodepaths already
        painted.
        """
        self._enabled = False
    
    def paint(self, nodepath):
        """Paint a nodepath with cartoon shading and inking."""
        if self._enabled:
            _inp = nodepath.instanceUnderNode(self.toon_render, nodepath.getName())
            _inp.setTag(self.CARTOON_SHADING_TAG, 'True')
            _inp.setTag(self.CARTOON_INKING_TAG, 'True')
            self._paintings[nodepath] = _inp
            nodepath.stash()
    
    def unpaint(self, nodepath):
        """Undo cartoon painting on a nodepath."""
        if self._enabled:
            if nodepath in self._paintings:
                _inp = self._paintings.pop(nodepath)
                _inp.removeNode()
                nodepath.unstash()
    
    def camera_spot_light(self, bool):
        """Enable or disable camera spot light effect. When enabled the shader
        light will follow the camera movements.
        """
        self._camera_spot_light = bool
    
    separation = property(get_separation, set_separation)
    cutoff = property(get_cutoff, set_cutoff)