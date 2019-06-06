"""Implement the graphical user interface for the Logic Simulator.

Used in the Logic Simulator project to enable the user to run the simulation
or adjust the network properties.

Classes:
--------
Gui - configures the main window and all the widgets.
MyGLCanvas - handles all canvas drawing operations.
Menubar - provides file, edit and view menus
Tab - a basis for the construction of the two tabs in the gui
SimulationTab - holds canvas and all the simulation controls
ControlPanel - holds all the simulation controls
SignalPanel - currently holds just the canvas - gives option to include more
              controls below the canvas
StatusBar - tiny display with instructions/messages for the user

"""

import wx
import wx.stc
import wx.glcanvas as wxcanvas
import numpy as np
import math
from OpenGL import GL, GLU, GLUT
from pathlib import Path

from names import Names
from devices import Devices
from network import Network
from monitors import Monitors
from scanner import Scanner
from parse import Parser


class Gui(wx.Frame):
    """Configure the main window and both tabs.

    This class provides a graphical user interface for the Logic Simulator and
    enables the user to change the circuit properties and run simulations.

    Parameters
    ----------
    title: title of the window.
    path: filepath of definition file.
    names: holds all keywords.
    devices: stores all logic devices and their properties.
    network: handles connection of circuit components.
    monitors: handles all operations of monitored signals.
    """

    def __init__(self, title, path, names, devices, network, monitors):
        """Initialise tabs."""
        super().__init__(parent=None, title=title, size=(800, 600))
        # Add menubar
        menubar = MenuBar(self)
        self.SetMenuBar(menubar)

        # Create tabs
        self.tab_holder = wx.Notebook(self)
        self.sim_tab = SimulationTab(self.tab_holder,
                                     names, devices, network, monitors)
        self.def_tab = DefinitionTab(self.tab_holder, path)
        self.tab_holder.AddPage(self.sim_tab, _("Simulation"))
        self.tab_holder.AddPage(self.def_tab, _("Definition File"))

        self.SetSizeHints(600, 600)  # Controls minimum parent window size


class MyGLCanvas(wxcanvas.GLCanvas):
    """Handle all drawing operations.

    This class contains functions for drawing onto the canvas. It
    also contains handlers for events relating to the canvas.

    Parameters
    ----------
    parent: parent widget - the signal panel
    names: instance of the names.Names() class.
    devices: instance of the devices.Devices() class.
    monitors: instance of the monitors.Monitors() class.

    dimension: sets the simulation view mode (2D or 3D)
    pan_x: horizontal pan for 2D view mode
    pan_y: vertical pan for 2D view mode
    pan_x_3D: horizontal pan for 3D view mode
    pan_y_3D: vertical pan for 3D view mode
    hbound: right horizontal bound on user's panning freedom
    hlbound: left horizontal bound on user's panning freedom
    vbound: upper vertical bound on user's panning freedom.
    hspace: constant offset of hbound from right canvas border.
    hlspace: offset of hlbound from left canvas border.
    vspace: offset of vbound from canvas border that accounts for height of
            drawn signals.
    zoom: holds the zoom of the view
    last_mouse_x:  previous x-coordinate held by cursor
    last_mouse_y: previous y-coordinate held by cursor

    mat_diffuse: describes matt surface
    mat_no_specular: describes matt surface with no mirror-like reflections
    mat_no_shininess: describes matt surface with no shine
    mat_specular: describes matt surface with mirror-like reflections
    mat_shininess: describes surface property
    top_right: refers to light position
    straight_on: refers to light position
    no_ambient: refers to lighting
    dim_diffuse: sets up dim diffuse light
    bright_diffuse: sets up bright diffuse light
    med_diffuse: sets up medium brightness diffuse light
    full_specular: describes fully reflective surface
    no_specular: describes surface with no mirror-like reflections

    scene_rotate: 4x4 matrix describing scene rotation
    depth_offset: offset between viewpoint and origin of the scene

    Public methods
    --------------
    init_gl(self): Configures the OpenGL context.

    init_gl_2D(self): Configures the 2D view mode.

    init_gl_3D(self): Configures the 3D view mode.

    render(self, text): Handles all drawing operations.

    get_signal_traces(self): Draws all signal traces.

    get_2D_signal_traces(self): Draws traces in 2D view mode.

    get_3D_signal_traces(self): Draws traces in 3D view mode.

    draw_cuboid(self, x_pos, z_pos, half_width, half_depth, height): Draws
        cuboid - building block of 3D traces

    on_paint(self, event): Handles the paint event.

    on_size(self, event): Handles the canvas resize event.

    on_mouse(self, event): Handles mouse events.

    render_text_2D(self, text, x_pos, y_pos, colour): Handles text drawing
                                              operations in 2D view.

    render_text_3D(self, text, x_pos, y_pos, z_pos, colour): Handles text
                                            drawing operations in 3D view.
    """

    def __init__(self, parent, names, devices, monitors):
        """Initialise canvas properties and useful variables."""
        super().__init__(parent, -1,
                         attribList=[wxcanvas.WX_GL_RGBA,
                                     wxcanvas.WX_GL_DOUBLEBUFFER,
                                     wxcanvas.WX_GL_DEPTH_SIZE, 16, 0])

        self.parent = parent
        self.names = names
        self.monitors = monitors
        self.devices = devices

        # Default view is 2D
        self.dimension = 2

        self.hspace = 100
        self.hlspace = 0
        self.vspace = 0

        # Initialise GL utilities and set the context to the canvas
        GLUT.glutInit()
        self.init = False
        self.context = wxcanvas.GLContext(self)

        # Initialise panning variables
        self.pan_x = 0
        self.pan_y = 0
        self.pan_x_3D = 0
        self.pan_y_3D = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        # Initialise variables for zooming
        self.zoom = 1

        # Bind events to widgets
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)

        # 3D View parameters for lighting and surfaces
        self.mat_diffuse = [0.0, 0.0, 0.0, 1.0]
        self.mat_no_specular = [0.0, 0.0, 0.0, 0.0]
        self.mat_no_shininess = [0.0]
        self.mat_specular = [0.5, 0.5, 0.5, 1.0]
        self.mat_shininess = [50.0]
        self.top_right = [1.0, 1.0, 1.0, 0.0]
        self.straight_on = [0.0, 0.0, 1.0, 0.0]
        self.no_ambient = [0.0, 0.0, 0.0, 1.0]
        self.dim_diffuse = [0.5, 0.5, 0.5, 1.0]
        self.bright_diffuse = [1.0, 1.0, 1.0, 1.0]
        self.med_diffuse = [0.75, 0.75, 0.75, 1.0]
        self.full_specular = [0.5, 0.5, 0.5, 1.0]
        self.no_specular = [0.0, 0.0, 0.0, 1.0]

        # Initialise the scene rotation matrix
        self.scene_rotate = np.identity(4, 'f')

        # Offset between viewpoint and origin of the scene
        self.depth_offset = 1000

    def init_gl(self):
        """Configure and initialise the OpenGL context."""

        if self.dimension == 2:
            self.init_gl_2D()
        else:
            self.init_gl_3D()

    def init_gl_2D(self):
        """Configure and initialise the 2D OpenGL context."""

        size = self.GetClientSize()

        # User's panning bounds depend on canvas size,
        # zoom and space signals occupy
        self.hbound = size.width - self.hspace * self.zoom
        self.vbound = size.height - self.vspace * self.zoom
        self.hlbound = -self.hlspace * self.zoom
        # Ensure positive gap between bounds to prevent 'jiggle' effect
        # if user zooms too much

        if self.hbound < self.hlbound:
            self.hbound = self.hlbound
        if self.vbound < 0:
            self.vbound = 0

        self.SetCurrent(self.context)

        GL.glDrawBuffer(GL.GL_BACK)
        GL.glClearColor(1.0, 1.0, 1.0, 0.0)
        # Specify dimensions of viewport rectangle
        GL.glViewport(0, 0, size.width, size.height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        # Specify clipping plane coordinates
        GL.glOrtho(0, size.width, 0, size.height, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslated(self.pan_x, self.pan_y, 0.0)
        GL.glScaled(self.zoom, self.zoom, self.zoom)

    def init_gl_3D(self):
        """Configure and initialise the 3D OpenGL context."""
        size = self.GetClientSize()

        self.SetCurrent(self.context)

        # Specify dimensions of viewport rectangle
        GL.glViewport(0, 0, size.width, size.height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(45, size.width / size.height, 10, 10000)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        # Set light properties: ambience, diffuse, specular and position
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, self.no_ambient)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, self.med_diffuse)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, self.no_specular)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, self.top_right)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_AMBIENT, self.no_ambient)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, self.dim_diffuse)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, self.no_specular)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, self.straight_on)

        # Specify the specular, shininess and ambience of front face
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, self.mat_specular)
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SHININESS, self.mat_shininess)
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE,
                        self.mat_diffuse)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)

        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glDrawBuffer(GL.GL_BACK)
        GL.glCullFace(GL.GL_BACK)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_LIGHT1)
        GL.glEnable(GL.GL_NORMALIZE)

        # Viewing transformation - set the viewpoint back from the scene
        GL.glTranslatef(0.0, 0.0, -self.depth_offset)

        # Translate, zoom, and rotate scene objects
        GL.glTranslatef(self.pan_x_3D, self.pan_y_3D, 0.0)
        GL.glMultMatrixf(self.scene_rotate)
        GL.glScalef(self.zoom, self.zoom, self.zoom)

    def render(self):
        """Handle all drawing operations."""
        self.SetCurrent(self.context)
        if not self.init:
            # Configure the viewport, modelview and projection matrices
            self.init_gl()
            self.init = True

        # Clear everything
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Draw signal traces
        self.get_signal_traces()

        # We have been drawing to the back buffer, flush the graphics pipeline
        # and swap the back buffer to the front.
        GL.glFlush()
        self.SwapBuffers()

    def on_paint(self, event):
        """Handle the paint event."""
        self.SetCurrent(self.context)
        if not self.init:
            # Configure the viewport, modelview and projection matrices
            self.init_gl()
            self.init = True
        self.render()

    def on_size(self, event):
        """Handle the canvas resize event.

        Forces reconfiguration of the viewport, modelview and projection
        matrices on the next paint event.
        """

        # Reset panning bounds
        size = self.GetClientSize()
        self.hbound = size.width - self.hspace * self.zoom
        self.vbound = size.height - self.vspace * self.zoom
        self.hlbound = -self.hlspace * self.zoom

        # Restrain pan values within bounds and bring signal within view
        if self.pan_x > self.hbound:
            self.pan_x = self.hbound
        elif self.pan_x < self.hlbound:
            self.pan_x = self.hlbound

        if self.pan_y > self.vbound:
            self.pan_y = self.vbound
        elif self.pan_y < 0:
            self.pan_y = 0

        self.init = False
        self.Refresh()  # Triggers paint event

    def on_mouse(self, event):
        """Handle mouse events."""
        self.SetCurrent(self.context)

        if event.ButtonDown():
            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            self.init = False

        # Restrain pan values within bounds
        if self.pan_x > self.hbound:
            self.pan_x = self.hbound
        elif self.pan_x < self.hlbound:
            self.pan_x = self.hlbound

        if self.pan_y > self.vbound:
            self.pan_y = self.vbound
        elif self.pan_y < 0:
            self.pan_y = 0

        if event.Dragging():
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()
            x = event.GetX() - self.last_mouse_x
            y = self.last_mouse_y - event.GetY()  # Reverse order to flip axes

            if self.dimension == 2:
                # Only pan if signal has not reached bounds
                if self.pan_x == self.hlbound and x < 0:
                    pass  # Do not update pan variable
                elif self.pan_x == self.hbound and x > 0:
                    pass
                else:
                    self.pan_x += x

                if self.pan_y == 0 and y < 0:
                    pass
                elif self.pan_y == self.vbound and y > 0:
                    pass
                else:
                    self.pan_y += y

                # Restrain pan values within bounds
                if self.pan_x > self.hbound:
                    self.pan_x = self.hbound
                elif self.pan_x < self.hlbound:
                    self.pan_x = self.hlbound

                if self.pan_y > self.vbound:
                    self.pan_y = self.vbound
                elif self.pan_y < 0:
                    self.pan_y = 0

            else:  # View is 3D
                if event.LeftIsDown():
                    GL.glRotatef(math.sqrt((x * x) + (y * y)), y, x, 0)
                if event.MiddleIsDown():
                    GL.glRotatef((x + y), 0, 0, 1)
                if event.RightIsDown():
                    self.pan_x_3D += x
                    self.pan_y_3D += y

                GL.glMultMatrixf(self.scene_rotate)
                GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX, self.scene_rotate)

            self.last_mouse_x = event.GetX()
            self.last_mouse_y = event.GetY()
            self.init = False

        if event.GetWheelRotation() < 0:
            self.zoom *= (1.0 + (
                event.GetWheelRotation() / (20 * event.GetWheelDelta())))
            self.init = False

        if event.GetWheelRotation() > 0:
            self.zoom /= (1.0 - (
                event.GetWheelRotation() / (20 * event.GetWheelDelta())))
            self.init = False

        # Bring signal into view on double click
        if event.LeftDClick():
            self.pan_x = 0
            self.pan_y = 0
            self.pan_x_3D = 0
            self.pan_y_3D = 0
            self.zoom = 1

            self.init = False

        self.Refresh()  # Triggers the paint event

    def get_signal_traces(self):
        """Get the signal traces from the monitors object."""
        if self.dimension == 2:
            self.get_2D_signal_traces()
        else:
            self.get_3D_signal_traces()

    def get_2D_signal_traces(self):
        """Get the signal traces from the monitors object and display in 2D."""

        # Exit function if no signals are being monitored
        if not self.monitors.monitors_dictionary:
            return

        y_pos = 20

        # Plot each signal in monitors_dictionary (holds all monitored signals)
        for device_id, output_id in self.monitors.monitors_dictionary:
            signal_list = self.monitors.monitors_dictionary[(device_id,
                                                             output_id)]

            text = self.names.get_name_string(device_id)

            # If device has more than one output ...
            if output_id:
                text += ("." + self.names.get_name_string(output_id))
            self.render_text_2D(text, 5, y_pos + 10)  # Display signal name.

            # Draw grey axis
            if len(signal_list) > 0:
                grey = [0.8, 0.8, 0.8]
                GL.glColor3fv(grey)
                x_next = 0
                y = 0
                y_up = 0
                y_down = 0
                i = 0

                for signal in signal_list:
                    GL.glBegin(GL.GL_LINES)

                    x = (i * 20) + 30
                    x_next = (i * 20) + 50
                    y = y_pos
                    y_up = y + 5
                    y_down = y - 5

                    GL.glVertex2f(x, y_up)
                    GL.glVertex2f(x, y_down)

                    GL.glVertex2f(x, y)
                    GL.glVertex2f(x_next, y)

                    GL.glEnd()

                    self.render_text_2D(str(i), x-2, y_down - 10, grey)
                    i += 1

                GL.glBegin(GL.GL_LINES)
                GL.glVertex2f(x_next, y_up)
                GL.glVertex2f(x_next, y_down)
                GL.glEnd()

                self.render_text_2D(str(i), x_next-2, y_down - 10, grey)

            # Draw signal
            GL.glColor3f(0.0, 0.0, 1.0)
            GL.glBegin(GL.GL_LINE_STRIP)
            drawing = True
            i = 0

            for signal in signal_list:
                if signal != self.devices.BLANK:
                    if not drawing:
                        GL.glBegin(GL.GL_LINE_STRIP)
                        drawing = True

                    if signal == self.devices.HIGH:
                        x = (i * 20) + 30
                        x_next = (i * 20) + 50
                        y = y_pos + 20
                        y_next = y
                    elif signal == self.devices.LOW:
                        x = (i * 20) + 30
                        x_next = (i * 20) + 50
                        y = y_pos
                        y_next = y
                    elif signal == self.devices.RISING:
                        x = (i * 20) + 30
                        x_next = x
                        y = y_pos
                        y_next = y_pos + 20
                    elif signal == self.devices.FALLING:
                        x = (i * 20) + 30
                        x_next = x
                        y = y_pos + 20
                        y_next = y_pos

                    GL.glVertex2f(x, y)
                    GL.glVertex2f(x_next, y_next)

                else:
                    if drawing:
                        GL.glEnd()
                        drawing = False

                i += 1

            GL.glEnd()
            y_pos += 60

    def get_3D_signal_traces(self):
        """Get the signal traces from the monitors object and display in 3D."""

        # Exit function if no signals are being monitored
        if not self.monitors.monitors_dictionary:
            return

        # define starting position of axis and rgb colours
        x_pos = 0
        white = [1.0, 1.0, 1.0]
        blue = [0.0, 0.0, 1.0]

        # length of one clock period in pixels
        cycle_length = 20

        # Plot each signal in monitors_dictionary (holds all monitored signals)
        for device_id, output_id in self.monitors.monitors_dictionary:
            # monitor_name = self.devices.get_signal_name(device_id, output_id)
            signal_list = self.monitors.monitors_dictionary[(device_id,
                                                             output_id)]
            cycles = len(signal_list)
            offset = cycle_length * cycles / 2  # Centre of gravity at origin.
            text = self.names.get_name_string(device_id)

            # If device has more than one output ...
            if output_id:
                text += ("." + self.names.get_name_string(output_id))

            GL.glColor3fv(white)  # Text is white
            self.render_text_3D(text, x_pos, 12,
                                -1.5*cycle_length - offset, blue)

            # Draw axis
            if cycles > 0:
                GL.glColor3fv(white)  # Axis is white

                i = 0
                z = 0
                z_pos = 0
                for signal in signal_list:
                    z_pos = i * cycle_length - offset
                    z = z_pos - cycle_length/2

                    self.draw_cuboid(x_pos+5.5, z, 5.5, 0.2, 1)
                    self.draw_cuboid(x_pos, z_pos, 0.2, cycle_length/2, 1)

                    # show every fifth axis label
                    if i % 5 == 0:
                        self.render_text_3D(str(i), x_pos, 1, z, white)

                    i += 1

                z_pos = i * cycle_length - offset
                z = z_pos - cycle_length/2
                self.draw_cuboid(x_pos+5.5, z, 5.5, 0.2, 1)

                # show every fifth axis label
                if i % 5 == 0:
                    self.render_text_3D(str(i), x_pos, 1, z, white)

                # define starting point for signal
                x_pos2 = x_pos + cycle_length

            GL.glColor3fv(blue)  # Signal is blue
            i = 0

            # Draw signal
            for signal in signal_list:
                z_pos = i * cycle_length - offset

                if signal == self.devices.HIGH:
                    self.draw_cuboid(x_pos2, z_pos, 5, cycle_length/2, 11)

                elif signal == self.devices.LOW:
                    self.draw_cuboid(x_pos2, z_pos, 5, cycle_length/2, 1)

                i += 1

            x_pos += 60

    def render_text_2D(self, text, x_pos, y_pos, colour=[1.0, 1.0, 1.0]):
        """Handle text drawing operations in 2D view."""

        GL.glColor3f(0.0, 0.0, 0.0)  # Text is black
        GL.glRasterPos2f(x_pos, y_pos)
        font = GLUT.GLUT_BITMAP_HELVETICA_12

        for character in text:
            if character == '\n':
                y_pos = y_pos - 20
                GL.glRasterPos2f(x_pos, y_pos)
            else:
                GLUT.glutBitmapCharacter(font, ord(character))

        GL.glColor3fv(colour)  # Restore colour used before function call.

    def render_text_3D(self, text, x_pos, y_pos, z_pos, colour):
        """Handle text drawing operations in 3D view."""
        GL.glDisable(GL.GL_LIGHTING)
        GL.glRasterPos3f(x_pos, y_pos, z_pos)
        font = GLUT.GLUT_BITMAP_HELVETICA_10

        for character in text:
            if character == '\n':
                y_pos = y_pos - 20
                GL.glRasterPos3f(x_pos, y_pos, z_pos)
            else:
                GLUT.glutBitmapCharacter(font, ord(character))

        GL.glEnable(GL.GL_LIGHTING)
        GL.glColor3fv(colour)  # Restore pre-function-call colour

    def draw_cuboid(self, x_pos, z_pos, half_width, half_depth, height):
        """Draw a cuboid.

        Draw a cuboid at the specified position, with the specified
        dimensions.
        """

        GL.glBegin(GL.GL_QUADS)
        GL.glNormal3f(0, -1, 0)
        GL.glVertex3f(x_pos - half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos + half_depth)
        GL.glNormal3f(0, 1, 0)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos + half_depth)
        GL.glNormal3f(-1, 0, 0)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos + half_depth)
        GL.glNormal3f(1, 0, 0)
        GL.glVertex3f(x_pos + half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos + half_depth)
        GL.glNormal3f(0, 0, -1)
        GL.glVertex3f(x_pos - half_width, -6, z_pos - half_depth)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos - half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos - half_depth)
        GL.glNormal3f(0, 0, 1)
        GL.glVertex3f(x_pos - half_width, -6 + height, z_pos + half_depth)
        GL.glVertex3f(x_pos - half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6, z_pos + half_depth)
        GL.glVertex3f(x_pos + half_width, -6 + height, z_pos + half_depth)
        GL.glEnd()


class SignalPanel(wx.Panel):
    """Create panel which holds the drawing canvas and allows provision for
       control to be added below the canvas.

       Parameters
       ----------
       parent: the parent window - the simulation tab
       canvas: the drawing canvas
       """

    def __init__(self, parent, names, devices, network, monitors):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.canvas = MyGLCanvas(self, names, devices, monitors)

        # Define signal panel layout.
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(box)


class ControlPanel(wx.Panel):
    """Create panel with all controls.

    Parameters
    ----------
    parent: parent window (simulation tab)
    names: instance of the Names class
    devices: instance of the Devices class
    network: instance of the Network class
    monitors: instance of the Monitors class

    txt_... : textboxes and labels
    list_... : checklist boxes
    btn_... : buttons
    spin: spin control

    cycles_completed: number of simulation cycles completed
                    since Run button pressed
    dimension: allows user to change view dimension
    num_signals_onscreen: holds the number of signals to be displayed
                                                        on the canvas.

    signal_names: holds the names of all signals
    switch_names: holds the names of all switches

    Public methods
    --------------
    on_run_button(self, event): starts execution of simulation when run button
                                                        is pressed.

    on_continue_button(self, event): continues execution of simulation
                                        on continue button.

    on_reset_button(self, event): resets simulation

    on_toggle_view(self, event): toggles between 2D and 3D view modes.

    run_network(self, cycles): runs network for specified no. of cycles.

    continue_network(self, cycles): continues running network for specified
                                                    no. of cycles.

    on_check_monitor(self, event): triggers monitor or zap command upon
                                                clicking checkbox.

    on_check_switches(self, event): sets state of switch upon
                                                clicking checkbox.

    monitor_command(self): adds signal to monitors dictionary.
    zap_command(self): removes signal from monitors dictionary.

    """
    def __init__(self, parent, names, devices, network, monitors):
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.names = names
        self.devices = devices
        self.network = network
        self.monitors = monitors
        self.cycles_completed = 0
        self.dimension = 2  # Default 2D view mode
        self.num_signals_onscreen = 0
        self.SetBackgroundColour('#767171')

        # Define fonts
        title_font = wx.Font('Helvetica')
        font = wx.Font('Helvetica')

        # Define control panel layout
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        hbox6 = wx.BoxSizer(wx.HORIZONTAL)
        hbox7 = wx.BoxSizer(wx.HORIZONTAL)
        hbox8 = wx.BoxSizer(wx.HORIZONTAL)
        hbox9 = wx.BoxSizer(wx.HORIZONTAL)
        hbox10 = wx.BoxSizer(wx.HORIZONTAL)

        # Get list of signal names
        self.signal_names = []
        for device in self.devices.devices_list:
            if next(iter(device.outputs)) is None:  # If no output list
                self.signal_names.append(self.names.
                                         get_name_string(device.device_id))
            else:
                for output_id in device.outputs:
                    self.signal_names.append(self.names.
                                             get_name_string(
                                                device.device_id) + '.' +
                                             self.names.
                                             get_name_string(output_id))

        # Get list of names of signals already monitored on startup
        self.init_monitored = []
        for (device_id, monitors_id) in self.monitors.monitors_dictionary:
            signal_name = self.names.get_name_string(device_id)
            if monitors_id is not None:
                signal_name = signal_name + '.' + \
                            self.names.get_name_string(monitors_id)
            self.init_monitored.append(signal_name)

        # Get indices of all monitored signals in signal_names list
        index = 0
        self.index_init_monitored = []
        for signal in self.signal_names:
            if signal in self.init_monitored:
                self.index_init_monitored.append(index)
            index += 1

        # Change panning range to accommodate monitored signals added onscreen
        self.num_signals_onscreen = len(self.index_init_monitored)
        self.parent.signal_panel.canvas.vspace = 40 * self.num_signals_onscreen

        # Get list of all switch names and all switches already closed
        # on startup
        self.switch_names = []
        self.init_set_switches = []
        for device in self.devices.devices_list:
            if device.device_kind == self.devices.SWITCH:
                self.switch_names.append(self.names.
                                         get_name_string(device.device_id))
                if device.switch_state == self.devices.HIGH:
                    # append name of closed switch to set_switches
                    self.init_set_switches.append(self.names.
                                                  get_name_string(device.
                                                                  device_id))

        # Get indices of all closed switches in set_switches
        self.index_set_switches = []
        index = 0
        for switch in self.switch_names:
            if switch in self.init_set_switches:
                self.index_set_switches.append(index)
            index += 1

        # Create widgets
        self.txt_heading = wx.StaticText(self, label=_("CONTROLS"))
        self.txt_monitor = wx.StaticText(self, label=_("Monitored signals"))
        self.txt_switches = wx.StaticText(self, label=_("Switches"))
        self.txt_cycles = wx.StaticText(self, label=_("No. cycles"))
        self.list_monitor = wx.CheckListBox(self,
                                            choices=self.signal_names,
                                            size=(-1, 75))
        self.list_monitor.SetCheckedItems(self.index_init_monitored)
        self.list_switches = wx.CheckListBox(self,
                                             choices=self.switch_names,
                                             size=(-1, 75))
        self.list_switches.SetCheckedItems(self.index_set_switches)
        self.txt_heading.SetFont(title_font)
        self.txt_monitor.SetFont(font)
        self.txt_switches.SetFont(font)
        self.txt_cycles.SetFont(font)
        self.btn_Run = wx.Button(self, label=_("Run"), style=wx.BORDER_NONE)
        self.btn_Continue = wx.Button(self, label=_("Continue"),
                                      style=wx.BORDER_NONE)
        self.btn_Toggle_View = wx.Button(self, label=_("Toggle 2D/3D View"),
                                         style=wx.BORDER_NONE)
        self.btn_Reset = wx.Button(self,
                                   label=_("Reset"),
                                   style=wx.BORDER_NONE)
        self.spin = wx.SpinCtrl(self)
        self.spin.SetValue(10)  # Default to 10 cycles

        # Bind events to widgets
        self.list_monitor.Bind(wx.EVT_CHECKLISTBOX, self.on_check_monitor)
        self.list_switches.Bind(wx.EVT_CHECKLISTBOX, self.on_check_switches)
        self.btn_Run.Bind(wx.EVT_BUTTON, self.on_run_button)
        self.btn_Continue.Bind(wx.EVT_BUTTON, self.on_continue_button)
        self.btn_Toggle_View.Bind(wx.EVT_BUTTON, self.on_toggle_view)
        self.btn_Reset.Bind(wx.EVT_BUTTON, self.on_reset_button)

        # Lay out widgets
        hbox1.Add(self.txt_heading)
        hbox2.Add(self.txt_monitor)
        hbox3.Add(self.list_monitor, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        hbox4.Add(self.txt_switches)
        hbox5.Add(self.list_switches, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        hbox6.Add(self.txt_cycles)
        hbox7.Add(self.spin, wx.EXPAND)
        hbox8.Add(self.btn_Run, flag=wx.RIGHT, border=8)
        hbox8.Add(self.btn_Continue)
        hbox9.Add(self.btn_Toggle_View, wx.EXPAND)
        hbox10.Add(self.btn_Reset, wx.EXPAND)
        vbox.Add(hbox1, flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(hbox2, flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(hbox3,
                 flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                 border=10)
        vbox.Add(hbox4, flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(hbox5,
                 flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                 border=10)
        vbox.Add(hbox6,
                 flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(hbox7,
                 flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                 border=10)
        vbox.Add(hbox8,
                 flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                 border=10)
        vbox.Add(hbox9,
                 flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP,
                 border=10)
        vbox.AddStretchSpacer()
        vbox.Add(hbox10, flag=wx.ALL | wx.EXPAND, border=10)

        # Format widgets
        self.txt_heading.SetForegroundColour('#ffffff')
        self.txt_monitor.SetForegroundColour('#ffffff')
        self.txt_switches.SetForegroundColour('#ffffff')
        self.txt_cycles.SetForegroundColour('#ffffff')
        self.list_monitor.SetBackgroundColour('#afabab')
        self.list_switches.SetBackgroundColour('#afabab')
        self.btn_Run.SetBackgroundColour('#afabab')
        self.btn_Continue.SetBackgroundColour('#afabab')
        self.btn_Toggle_View.SetBackgroundColour('#afabab')
        self.btn_Reset.SetBackgroundColour('#afabab')

        # Set control panel layout
        self.SetSizer(vbox)

    def on_run_button(self, event):
        """Handle the event when the user clicks the run button."""

        cycles = self.spin.GetValue()
        # self.cycles_completed += cycles
        self.monitors.reset_monitors()
        self.devices.cold_startup()

        if not self.run_network(cycles):
            text = _("Error: Could not run network")
        elif cycles == 0:
            # Reset variable to ensure that simulation won't attempt
            # to continue after it has not run at all.
            self.cycles_completed = 0

            # Empty canvas
            self.parent.signal_panel.canvas.monitors.reset_monitors()
            self.parent.signal_panel.canvas.render()
            text = ""
        else:
            text = _("Simulation run for ") + str(cycles) + _(" cycles.")

        # No event when simulation reset
        if event == _:
            text = _("Simulation reset.")

        self.parent.status_bar.set_status(text)

    def on_continue_button(self, event):
        """Handle the event when the user clicks the continue button."""

        cycles = self.spin.GetValue()
        if self.cycles_completed == 0:
                text = _("Error! Nothing to continue. Run first.")

        else:
            self.continue_network(cycles)
            text = (_("Simulation continued for ") + str(cycles) +
                    _(" more cycles."))
        self.parent.status_bar.set_status(text)

    def on_reset_button(self, event):
        """Handle the event when the user clicks the reset button.

        Restore the gui to its initial state.
        """
        self.cycles_completed = 0
        index = 0

        # Reset monitors dictionary
        for item in self.signal_names:
            # Get signal id
            [self.device_id, self.output_id] = self.devices. \
                                                    get_signal_ids(item)

            if not self.list_monitor.IsChecked(index):
                if item in self.init_monitored:
                    self.monitor_command()

            elif self.list_monitor.IsChecked(index):
                if item not in self.init_monitored:
                    self.zap_command()

            index += 1

        index = 0

        # Reset switches
        for item in self.switch_names:
            switch = self.switch_names[index]
            on = self.list_switches.IsChecked(index)
            if not(on) and (item in self.init_set_switches):
                # Turn switch on
                switch_id = self.devices.get_signal_ids(switch)[0]
                self.devices.set_switch(switch_id, 1)
            elif on and (item not in self.init_set_switches):
                # Turn switch off
                switch_id = self.devices.get_signal_ids(switch)[0]
                self.devices.set_switch(switch_id, 0)
            index += 1

        # Reset widgets
        self.spin.SetValue(10)
        self.list_monitor.SetCheckedItems(self.index_init_monitored)
        self.list_switches.SetCheckedItems(self.index_set_switches)

        # Reset the canvas
        self.on_run_button(_)

    def on_toggle_view(self, event):
        """Handle the event when the user toggles between 2D/3D view."""

        # Force reconfiguration of canvas.
        self.parent.signal_panel.canvas.init = False

        if self.dimension == 2:
            self.dimension = 3

        elif self.dimension == 3:
            self.dimension = 2

        self.parent.signal_panel.canvas.dimension = self.dimension
        self.parent.signal_panel.canvas.Refresh()

    def run_network(self, cycles):
        """Run the network for the specified number of simulation cycles.

        Return True if successful.
        """
        # Update canvas bounds
        self.parent.signal_panel.canvas.vspace = 40 * self.num_signals_onscreen
        self.parent.signal_panel.canvas.hlspace = self.cycles_completed * 20

        # Reset pan and zoom on run
        self.parent.signal_panel.canvas.pan_x = 0
        self.parent.signal_panel.canvas.pan_y = 0
        self.parent.signal_panel.canvas.pan_x_3D = 0
        self.parent.signal_panel.canvas.pan_y_3D = 0
        self.parent.signal_panel.canvas.zoom = 1
        self.parent.signal_panel.canvas.init = False

        # Reset number of cycles completed
        self.cycles_completed = cycles

        # Record signals and render.  Otherwise display error message.
        for _ in range(cycles):
            if self.network.execute_network():
                self.monitors.record_signals()
                self.parent.signal_panel.canvas.render()
            else:
                self.parent.status_bar.set_status(
                        _("Error! Network oscillating."))
                return False

        return True

    def continue_network(self, cycles):
        """Continue the simulation for the specified number of
        simulation cycles.
        """
        # Update number of cycles completed
        self.cycles_completed += cycles

        # Update canvas bounds
        self.parent.signal_panel.canvas.hlspace = self.cycles_completed * 20

        # Record signals and render.  Otherwise display error message.
        for _ in range(cycles):
            if self.network.execute_network():
                self.monitors.record_signals()
                self.parent.signal_panel.canvas.render()
            else:
                self.parent.status_bar.set_status(
                        _("Error! Network oscillating."))
                return False

    def on_check_monitor(self, event):
        """Handle the event when a signal is selected to monitor."""

        # Get name of signal that has been checked/unchecked
        # in monitors listbox.
        list_index = event.GetInt()
        self.signal_name = self.signal_names[list_index]

        # Get signal id
        [self.device_id, self.output_id] = self.devices. \
            get_signal_ids(self.signal_name)

        # Make monitor if box checked, otherwise remove monitor
        if self.list_monitor.IsChecked(list_index):
            self.monitor_command()
        else:
            self.zap_command()

    def on_check_switches(self, event):
        """Change state of specified switch."""

        # Get new switch state
        list_index = event.GetInt()
        switch = self.switch_names[list_index]
        state = self.list_switches.IsChecked(list_index)

        # Status bar message
        state_word = [_("turned off."), _("turned on.")]
        text = _("Switch ") + switch + _(" has been ") + state_word[state]

        # Set switch state
        switch_id = self.devices.get_signal_ids(switch)[0]
        self.devices.set_switch(switch_id, state)

        # Update canvas device
        self.parent.signal_panel.canvas.devices = self.devices
        self.parent.status_bar.set_status(text)

    def monitor_command(self):
        """Set the specified monitor."""

        monitor_error = self.monitors.make_monitor(self.device_id,
                                                   self.output_id,
                                                   self.cycles_completed)
        if monitor_error == self.monitors.NO_ERROR:
            self.parent.status_bar.set_status(_("Now monitoring ") +
                                              self.signal_name)
            print(_("Successfully made monitor."))
            self.num_signals_onscreen += 1
        else:
            print(_("Error! Could not make monitor."))

        # Update canvas monitors
        self.parent.signal_panel.canvas.monitors = self.monitors

    def zap_command(self):
        """Remove the specified monitor."""

        if self.monitors.remove_monitor(self.device_id, self.output_id):
            self.parent.status_bar.set_status(_("No longer monitoring ") +
                                              self.signal_name)
            print(_("Successfully zapped monitor."))
            self.num_signals_onscreen -= 1
        else:
            print(_("Error! Could not zap monitor."))

        # Update canvas monitors
        self.parent.signal_panel.canvas.monitors = self.monitors


class Tab(wx.Panel):
    """Create a tab for the main window."""

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)


class SimulationTab(Tab):
    """Create Tab with control panel and signal panel (which holds canvas).

    Parameters
    ----------
    signal_panel: instance of SignalPanel class.
    control_panel: instance of ControlPanel class.
    status_bar: instance of StatusBar class.
    hbox: main sizer of tab - controls layout of panels within it.

    """

    def __init__(self, parent, names, devices, network, monitors):
        Tab.__init__(self, parent)

        # Set up signal panel (holds canvas), control panel and status bar.
        self.signal_panel = SignalPanel(self, names,
                                        devices, network, monitors)
        self.control_panel = ControlPanel(self, names,
                                          devices, network, monitors)
        self.status_bar = StatusBar(self, size=(-1, 25))

        # Set layout
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox.Add(self.signal_panel, 1, wx.EXPAND)
        self.hbox.Add(self.control_panel, 0, wx.EXPAND)
        vbox.Add(self.hbox, 1, wx.EXPAND)
        vbox.Add(self.status_bar, 0, wx.EXPAND)

        self.SetSizer(vbox)


class DefinitionTab(Tab):
    """ Create tab with file tree and textbox holding displaying
    definition file.

    Parameters
    ----------
    parent: the parent widget (tab_holder - an instance of wx.Notebook)

    Public methods
    --------------
    on_return button: load new definition file into text box on return button

    """

    def __init__(self, parent, init_path):

        Tab.__init__(self, parent)

        # Create sizer to setup layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create splitter window
        self.splitter = wx.SplitterWindow(self, style=wx.SP_3D)

        # Heading with filename
        fname = wx.StaticText(self, label=str(init_path))

        # textbox for definition file
        self.text = wx.TextCtrl(self.splitter, style=wx.TE_MULTILINE)
        self.text.LoadFile(init_path)
        self.text.SetBackgroundColour('#f2f2f2')

        # Create directory tree
        home_dir = str(Path.home())
        self.dirWid = wx.GenericDirCtrl(self.splitter, dir=home_dir)
        tree = self.dirWid.GetTreeCtrl()

        # Bind event to directory tree
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.on_return_button, id=tree.GetId())

        # Add directory tree and text box to splitter window
        self.splitter.SplitVertically(self.text, self.dirWid, 500)
        self.splitter.SetMinimumPaneSize(200)

        # Setup layout
        self.SetSizer(main_sizer)
        main_sizer.Add(fname)
        main_sizer.Add(self.splitter, 1, wx.EXPAND)

        # File management not fully functional yet so removed in maintenance
        self.splitter.Unsplit()

    def on_return_button(self, event):
        """Display new definition file in text box on selection of file and
        press on the return button.

        """

        key = event.GetKeyCode()
        if key == wx.stc.STC_KEY_RETURN:
            filepath = self.dirWid.GetFilePath()
            self.text.LoadFile(filepath)


class MenuBar(wx.MenuBar):
    """Configure the menu bar.

    Parameters
    ----------
    cp: calls toggle_control_panel to toggle visibility of controls.
    fm: calls toggle_file_manager to toggle visibility of the file manager.

    Public methods
    --------------
    toggle_control_panel(self): toggles the visibility of controls.
    toggle_file_manager(self): toggles the visibility of the file manager.

    """

    def __init__(self, parent):
        wx.MenuBar.__init__(self)

        self.parent = parent

        # Configure menus and menu bar.
        fileMenu = wx.Menu()
        showMenu = wx.Menu()
        viewMenu = wx.Menu()
        # fileMenu.Append(wx.ID_OPEN, _("&Open"))
        fileMenu.Append(wx.ID_ABOUT, _("&About"))
        fileMenu.Append(wx.ID_EXIT, _("&Exit"))
        self.cp = showMenu.Append(1, _("Controls"), kind=wx.ITEM_CHECK)
        # File management not fully functional so removed during maintenance
        # self.fm = showMenu.Append(2, _("File Manager"), kind=wx.ITEM_CHECK)
        self.cp.Check()
        # self.fm.Check()
        viewMenu.AppendSubMenu(showMenu, _("Show/Hide"))
        self.Append(fileMenu, _("&File"))
        self.Append(viewMenu, _("&View"))

        # Bind events to menu items.
        self.Bind(wx.EVT_MENU, self.on_menu)

    def on_menu(self, event):
        """Handle the event when the user selects a menu item."""
        Id = event.GetId()
        if Id == wx.ID_EXIT:
            self.parent.Close(True)
        if Id == wx.ID_ABOUT:
            wx.MessageBox(_("Logic Simulator\nCreated by Group 14\nJune 2019"),
                          _("About Logsim"), wx.ICON_INFORMATION | wx.OK)

        # if Id == wx.ID_OPEN:
        #    self.parent.tab_holder.SetSelection(1)  # Show file tree.

        if Id == 1:
            self.toggle_control_panel()  # Show/hide controls.
        if Id == 2:
            self.toggle_file_manager()  # Show/hide file manager.

    def toggle_control_panel(self):
        """Toggle visibility of the control panel."""

        control_panel = self.parent.sim_tab.control_panel
        hbox = self.parent.sim_tab.hbox

        if self.cp.IsChecked():
            hbox.Show(control_panel)
            hbox.Layout()
        else:
            hbox.Hide(control_panel)
            hbox.Layout()

    def toggle_file_manager(self):
        """Toggle visibility of the file manager."""

        splitter = self.parent.def_tab.splitter
        text = self.parent.def_tab.text
        dirWid = self.parent.def_tab.dirWid

        if self.fm.IsChecked():

            splitter.SplitVertically(text, dirWid)
        else:
            splitter.Unsplit()


class StatusBar(wx.Panel):
    """Sets up a status bar for displaying messages to the user.

    Public methods
    --------------
    set_status(self, status): changes the displayed text

    """

    def __init__(self, parent, size):
        super().__init__(parent, size=size)
        self.SetBackgroundColour('#afabab')
        self.text = wx.StaticText(parent=self)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.text, flag=wx.LEFT, border=10)
        self.SetSizer(box)

    def set_status(self, status):
        """Change the status."""

        self.text.SetLabel(status)
