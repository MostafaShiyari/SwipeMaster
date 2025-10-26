from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import QPainter, QCursor, QPen, QColor, QPixmap, QIcon
from qgis.PyQt.QtWidgets import (QDialog, QHBoxLayout, QLabel, QComboBox, 
                                QPushButton, QMessageBox, QColorDialog, QAction)
from qgis.gui import QgsMapTool, QgsMapCanvasItem
from qgis.core import QgsMapSettings, QgsMapRendererCustomPainterJob
from qgis.utils import iface
import os

class SwipeMasterPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.control_panel = None
        # Get the directory where this plugin is located
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Create icon path
        icon_path = os.path.join(self.plugin_dir, 'swipemaster.png')
        
        self.action = QAction(
            QIcon(icon_path),
            "SwipeMaster",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("SwipeMaster", self.action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu("SwipeMaster", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.control_panel:
            self.control_panel.close()

    def run(self):
        """Run method that performs all the real work"""
        if self.control_panel is None or not self.control_panel.isVisible():
            self.control_panel = MinimalSwipeControlPanel()
        self.control_panel.show()
        self.control_panel.raise_()
        self.control_panel.activateWindow()


class MinimalSwipeControlPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SwipeMaster - Swipe Tool")
        self.setModal(False)
        self.setFixedSize(600, 60)
        
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        
        self.selected_layer = None
        self.current_tool = None
        self.swipe_direction = "right"  # Default direction: right
        
        # Default settings
        self.line_color = QColor(255, 0, 0, 200)
        self.line_width = 3
        self.line_opacity = 200
        self.layer_opacity = 0.0  # Default layer opacity in hidden area
        
        self.setup_ui()
        self.load_layers()
        self.position_panel()
        
    def position_panel(self):
        screen_geometry = iface.mainWindow().screen().availableGeometry()
        panel_width = self.width()
        x = screen_geometry.width() - panel_width - 20
        y = 50
        self.move(x, y)
        
    def create_color_icon(self, color):
        pixmap = QPixmap(20, 20)
        pixmap.fill(color)
        return QIcon(pixmap)
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(3)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Layer combo box
        self.layer_combo = QComboBox()
        self.layer_combo.setMinimumWidth(80)
        self.layer_combo.setMaximumWidth(120)
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        main_layout.addWidget(self.layer_combo)
        
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #ccc;")
        sep1.setFixedWidth(5)
        main_layout.addWidget(sep1)
        
        # Direction combo box - with text labels
        self.direction_combo = QComboBox()
        self.direction_combo.setFixedWidth(70)
        self.direction_combo.addItem("Right", "right")
        self.direction_combo.addItem("Left", "left")
        self.direction_combo.addItem("Top", "top")
        self.direction_combo.addItem("Bottom", "bottom")
        self.direction_combo.currentIndexChanged.connect(self.on_direction_changed)
        self.direction_combo.setToolTip("Swipe direction")
        main_layout.addWidget(self.direction_combo)
        
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #ccc;")
        sep2.setFixedWidth(5)
        main_layout.addWidget(sep2)
        
        # Color combo box
        self.color_combo = QComboBox()
        self.color_combo.setFixedWidth(60)
        
        # Colors with icons and hidden names
        colors = [
            (QColor(255, 0, 0), "🔴"),
            (QColor(0, 255, 0), "🟢"), 
            (QColor(0, 0, 255), "🔵"),
            (QColor(255, 255, 0), "🟡"),
            (QColor(255, 255, 255), "⚪"),
            (QColor(0, 0, 0), "⚫")
        ]
        
        for color, emoji in colors:
            self.color_combo.addItem(emoji, color)
        
        self.color_combo.addItem("🎨", None)  # Custom color option
        
        self.color_combo.currentIndexChanged.connect(self.on_color_changed)
        self.color_combo.setToolTip("Line color")
        main_layout.addWidget(self.color_combo)
        
        sep3 = QLabel("|")
        sep3.setStyleSheet("color: #ccc;")
        sep3.setFixedWidth(5)
        main_layout.addWidget(sep3)
        
        # Thickness combo box - with simple numbers
        self.thickness_combo = QComboBox()
        self.thickness_combo.setFixedWidth(60)
        
        thickness_options = [
            ("1px", 1),
            ("2px", 2),
            ("3px", 3),
            ("4px", 4),
            ("5px", 5),
            ("6px", 6),
            ("8px", 8),
            ("10px", 10)
        ]
        
        for text, thickness in thickness_options:
            self.thickness_combo.addItem(text, thickness)
        
        self.thickness_combo.setCurrentIndex(2)  # 3px thickness
        self.thickness_combo.currentIndexChanged.connect(self.on_thickness_changed)
        self.thickness_combo.setToolTip("Line thickness")
        main_layout.addWidget(self.thickness_combo)
        
        sep4 = QLabel("|")
        sep4.setStyleSheet("color: #ccc;")
        sep4.setFixedWidth(5)
        main_layout.addWidget(sep4)
        
        # Opacity combo box - with percentage numbers
        self.opacity_combo = QComboBox()
        self.opacity_combo.setFixedWidth(50)
        self.opacity_combo.addItem("100%", 255)
        self.opacity_combo.addItem("75%", 191)
        self.opacity_combo.addItem("50%", 128)
        self.opacity_combo.addItem("25%", 64)
        self.opacity_combo.addItem("0%", 0)
        self.opacity_combo.setCurrentIndex(2)  # 50%
        self.opacity_combo.currentIndexChanged.connect(self.on_opacity_changed)
        self.opacity_combo.setToolTip("Line opacity")
        main_layout.addWidget(self.opacity_combo)
        
        sep5 = QLabel("|")
        sep5.setStyleSheet("color: #ccc;")
        sep5.setFixedWidth(5)
        main_layout.addWidget(sep5)
        
        # Layer Opacity combo box - NEW FEATURE
        self.layer_opacity_combo = QComboBox()
        self.layer_opacity_combo.setFixedWidth(80)
        self.layer_opacity_combo.addItem("Hidden: 100%", 1.0)
        self.layer_opacity_combo.addItem("Hidden: 75%", 0.75)
        self.layer_opacity_combo.addItem("Hidden: 50%", 0.5)
        self.layer_opacity_combo.addItem("Hidden: 25%", 0.25)
        self.layer_opacity_combo.addItem("Hidden: 0%", 0.0)
        self.layer_opacity_combo.setCurrentIndex(4)  # 0% default (completely hidden)
        self.layer_opacity_combo.currentIndexChanged.connect(self.on_layer_opacity_changed)
        self.layer_opacity_combo.setToolTip("Layer opacity in hidden area")
        main_layout.addWidget(self.layer_opacity_combo)
        
        sep6 = QLabel("|")
        sep6.setStyleSheet("color: #ccc;")
        sep6.setFixedWidth(5)
        main_layout.addWidget(sep6)
        
        # Start button
        self.start_button = QPushButton("▶️")
        self.start_button.setFixedWidth(40)
        self.start_button.clicked.connect(self.start_tool)
        self.start_button.setToolTip("Activate tool")
        self.start_button.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 5px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        main_layout.addWidget(self.start_button)
        
        # Close button
        self.cancel_button = QPushButton("❌")
        self.cancel_button.setFixedWidth(40)
        self.cancel_button.clicked.connect(self.close_application)
        self.cancel_button.setToolTip("Close")
        self.cancel_button.setStyleSheet("""
            QPushButton { 
                background-color: #f44336; 
                color: white; 
                font-weight: bold; 
                padding: 5px;
                border: none;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.cancel_button)
        
        # Status
        self.status_label = QLabel("⏸️")
        self.status_label.setFixedWidth(30)
        self.status_label.setToolTip("Status: Inactive")
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        main_layout.addWidget(self.status_label)
        
    def on_direction_changed(self):
        if self.direction_combo.currentIndex() >= 0:
            self.swipe_direction = self.direction_combo.currentData()
            self.update_status("✅", f"Direction: {self.swipe_direction.capitalize()}")
            
        if self.current_tool:
            self.current_tool.swipe_direction = self.swipe_direction
            self.current_tool.update_overlay_direction()
        
    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        
    def load_layers(self):
        layers = iface.mapCanvas().layers()
        self.layer_combo.clear()
        
        for layer in layers:
            layer_name = layer.name()
            if len(layer_name) > 15:
                layer_name = layer_name[:12] + "..."
            self.layer_combo.addItem(layer_name, layer)
            
        if layers:
            self.selected_layer = layers[0]
            self.update_status("✅", "Ready")
        else:
            self.update_status("❌", "Error")
        
    def on_layer_changed(self):
        if self.layer_combo.currentIndex() >= 0:
            self.selected_layer = self.layer_combo.currentData()
            
            # If tool is active, stop it completely
            if self.current_tool:
                # First reset opacity of previous layer
                if self.current_tool.layer:
                    self.current_tool.layer.setOpacity(1)
                    self.current_tool.layer.triggerRepaint()
                
                # Then deactivate the tool
                self.current_tool.deactivate()
                # Ensure complete cleanup
                if hasattr(self.current_tool, 'cleanup'):
                    self.current_tool.cleanup()
                self.current_tool = None
                
            # Reset status
            self.update_status("✅", "Layer changed - Ready to activate")
            self.start_button.setEnabled(True)
                
    def on_color_changed(self):
        if self.color_combo.currentData() is None:
            color = QColorDialog.getColor(self.line_color, self, "Select line color")
            if color.isValid():
                self.line_color = color
                self.line_color.setAlpha(self.line_opacity)
        else:
            self.line_color = self.color_combo.currentData()
            self.line_color.setAlpha(self.line_opacity)
            
        # Apply changes
        self.apply_settings_to_tool()
                
    def on_thickness_changed(self):
        self.line_width = self.thickness_combo.currentData()
        
        # Apply changes
        self.apply_settings_to_tool()
                
    def on_opacity_changed(self):
        self.line_opacity = self.opacity_combo.currentData()
        self.line_color.setAlpha(self.line_opacity)
        
        # Apply changes
        self.apply_settings_to_tool()
        
    def on_layer_opacity_changed(self):
        """When layer opacity is changed"""
        self.layer_opacity = self.layer_opacity_combo.currentData()
        self.apply_layer_opacity_settings()
        
    def apply_layer_opacity_settings(self):
        """Apply layer opacity to active tool"""
        if self.current_tool:
            self.current_tool.layer_opacity = self.layer_opacity
            self.current_tool.update_layer_opacity()
        
    def apply_settings_to_tool(self):
        """Apply settings to active tool"""
        if self.current_tool:
            # Update settings in tool
            self.current_tool.line_color = self.line_color
            self.current_tool.line_width = self.line_width
            
            # If overlay exists, update it
            if self.current_tool.overlay:
                self.current_tool.overlay.set_line_style(self.line_color, self.line_width)
        
    def update_status(self, icon, tooltip=""):
        self.status_label.setText(icon)
        self.status_label.setToolTip(tooltip)
        
        if icon in ["✅", "🔄"]:
            self.status_label.setStyleSheet("color: green; font-size: 14px;")
        elif icon == "❌":
            self.status_label.setStyleSheet("color: red; font-size: 14px;")
        else:
            self.status_label.setStyleSheet("color: blue; font-size: 14px;")
            
    def start_tool(self):
        if not self.selected_layer:
            QMessageBox.warning(self, "Error", "Please select a layer!")
            return
            
        try:
            # Ensure cleanup of previous tool
            if self.current_tool:
                self.current_tool.deactivate()
                if hasattr(self.current_tool, 'cleanup'):
                    self.current_tool.cleanup()
                self.current_tool = None
                
            canvas = iface.mapCanvas()
            self.current_tool = SplitSwipeTool(canvas, self.selected_layer, self.line_color, self.line_width, self, self.swipe_direction, self.layer_opacity)
            
            # Create overlay immediately after activating tool
            self.current_tool.create_overlay()
            
            canvas.setMapTool(self.current_tool)
            
            self.update_status("🔄", f"Active - Direction: {self.swipe_direction.capitalize()}")
            self.start_button.setEnabled(False)
            
            self.raise_()
            self.activateWindow()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error activating tool: {str(e)}")
    
    def tool_deactivated(self):
        # Only update status but don't clean up tool
        # It might be managed by on_layer_changed
        self.update_status("✅", f"Ready - Direction: {self.swipe_direction.capitalize()}")
        self.start_button.setEnabled(True)
            
    def close_application(self):
        if self.current_tool:
            self.current_tool.deactivate()
            if hasattr(self.current_tool, 'cleanup'):
                self.current_tool.cleanup()
        self.close()
        
    def closeEvent(self, event):
        if self.current_tool:
            self.current_tool.deactivate()
            if hasattr(self.current_tool, 'cleanup'):
                self.current_tool.cleanup()
        event.accept()

class SplitSwipeOverlay(QgsMapCanvasItem):
    def __init__(self, canvas, layer, line_color=QColor(255, 0, 0, 200), line_width=3, swipe_direction="right"):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.swipe_direction = swipe_direction
        
        # Initial line position based on direction
        if swipe_direction in ["right", "left"]:
            self.split_position = canvas.width() // 2
        else:  # top, bottom
            self.split_position = canvas.height() // 2
            
        self.setZValue(1000)
        
        self.line_color = line_color
        self.line_width = line_width
        
        self.canvas.extentsChanged.connect(self.update_cache)
        self.canvas.scaleChanged.connect(self.update_cache)
        
        self.cached_image = None
        self.update_cache()
        self.show()

    def update_cache(self):
        try:
            self.cached_image = self.canvas.grab().toImage()
        except Exception as e:
            self.cached_image = None

    def set_line_style(self, color, width):
        """Set line style"""
        self.line_color = color
        self.line_width = width
        self.update()
        self.canvas.refresh()
        
    def set_direction(self, swipe_direction):
        """Change overlay direction"""
        self.swipe_direction = swipe_direction
        if swipe_direction in ["right", "left"]:
            self.split_position = self.canvas.width() // 2
        else:  # top, bottom
            self.split_position = self.canvas.height() // 2
        self.update()
        self.canvas.refresh()

    def set_split_position(self, pos):
        if self.swipe_direction in ["right", "left"]:
            self.split_position = max(0, min(pos, self.canvas.width()))
        else:  # top, bottom
            self.split_position = max(0, min(pos, self.canvas.height()))
        self.update()
        self.canvas.refresh()

    def paint(self, painter, option, widget=None):
        if not self.cached_image:
            return

        painter.save()
        
        try:
            # Set pen with current specifications
            pen = QPen(self.line_color)
            pen.setWidth(self.line_width)
            painter.setPen(pen)
            
            if self.swipe_direction == "right":
                # Swipe from right: left of line shows base layer, right shows selected layer
                clip_rect = QRectF(0, 0, self.split_position, self.canvas.height())
                painter.setClipRect(clip_rect)
                painter.drawImage(0, 0, self.cached_image)
                
                # Draw separator line
                painter.setClipping(False)
                painter.drawLine(self.split_position, 0, self.split_position, self.canvas.height())
                
            elif self.swipe_direction == "left":
                # Swipe from left: right of line shows base layer, left shows selected layer
                clip_rect = QRectF(self.split_position, 0, self.canvas.width() - self.split_position, self.canvas.height())
                painter.setClipRect(clip_rect)
                painter.drawImage(0, 0, self.cached_image)
                
                # Draw separator line
                painter.setClipping(False)
                painter.drawLine(self.split_position, 0, self.split_position, self.canvas.height())
                
            elif self.swipe_direction == "top":
                # Swipe from top: below line shows base layer, above shows selected layer
                clip_rect = QRectF(0, self.split_position, self.canvas.width(), self.canvas.height() - self.split_position)
                painter.setClipRect(clip_rect)
                painter.drawImage(0, 0, self.cached_image)
                
                # Draw separator line
                painter.setClipping(False)
                painter.drawLine(0, self.split_position, self.canvas.width(), self.split_position)
                
            elif self.swipe_direction == "bottom":
                # Swipe from bottom: above line shows base layer, below shows selected layer
                clip_rect = QRectF(0, 0, self.canvas.width(), self.split_position)
                painter.setClipRect(clip_rect)
                painter.drawImage(0, 0, self.cached_image)
                
                # Draw separator line
                painter.setClipping(False)
                painter.drawLine(0, self.split_position, self.canvas.width(), self.split_position)
            
        except Exception as e:
            pass
        finally:
            painter.restore()

    def cleanup(self):
        try:
            self.canvas.extentsChanged.disconnect(self.update_cache)
            self.canvas.scaleChanged.disconnect(self.update_cache)
            # Remove from scene
            if self.canvas.scene():
                self.canvas.scene().removeItem(self)
        except:
            pass

class SplitSwipeTool(QgsMapTool):
    def __init__(self, canvas, layer, line_color, line_width, control_panel, swipe_direction="right", layer_opacity=0.0):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.control_panel = control_panel
        self.overlay = None
        self.dragging = False
        self.last_mouse_pos = None
        self.swipe_direction = swipe_direction
        self.layer_opacity = layer_opacity  # New parameter for layer opacity
        
        self.line_color = line_color
        self.line_width = line_width
        
        # Set cursor based on direction
        self.update_cursor()
    
    def update_cursor(self):
        """Update cursor based on direction"""
        if self.swipe_direction in ["right", "left"]:
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:  # top, bottom
            self.setCursor(QCursor(Qt.SizeVerCursor))
    
    def create_overlay(self):
        """Create overlay with current settings"""
        # Remove previous overlay if exists
        if self.overlay:
            self.overlay.cleanup()
            self.canvas.scene().removeItem(self.overlay)
            self.overlay = None
            
        self.overlay = SplitSwipeOverlay(self.canvas, self.layer, self.line_color, self.line_width, self.swipe_direction)
        
        # Set initial position
        if self.swipe_direction in ["right", "left"]:
            self.overlay.set_split_position(self.canvas.width() // 2)
        else:  # top, bottom
            self.overlay.set_split_position(self.canvas.height() // 2)
            
    def update_overlay_direction(self):
        """Update overlay direction"""
        if self.overlay:
            self.overlay.set_direction(self.swipe_direction)
        
        self.update_cursor()
    
    def update_layer_opacity(self):
        """Update layer opacity based on current position"""
        if not self.layer or not self.overlay:
            return
            
        # Apply the layer opacity setting to the appropriate side based on direction
        if self.swipe_direction == "right":
            # Right side: full opacity, left side: configured opacity
            self.layer.setOpacity(self.layer_opacity)
        elif self.swipe_direction == "left":
            # Left side: full opacity, right side: configured opacity
            self.layer.setOpacity(self.layer_opacity)
        elif self.swipe_direction == "top":
            # Top side: full opacity, bottom side: configured opacity
            self.layer.setOpacity(self.layer_opacity)
        elif self.swipe_direction == "bottom":
            # Bottom side: full opacity, top side: configured opacity
            self.layer.setOpacity(self.layer_opacity)
            
        self.layer.triggerRepaint()
    
    def activate(self):
        super().activate()
        self.control_panel.update_status("🔄", f"Active - Direction: {self.swipe_direction.capitalize()}")
        
    def deactivate(self):
        # Only call cleanup but don't remove overlay
        # It might be managed by control panel
        self.cleanup_soft()
        super().deactivate()
        self.control_panel.tool_deactivated()
        
    def cleanup(self):
        """Complete cleanup"""
        self.cleanup_soft()
        
    def cleanup_soft(self):
        """Soft cleanup without affecting control panel status"""
        if self.overlay:
            self.overlay.cleanup()
            self.canvas.scene().removeItem(self.overlay)
            self.overlay = None
            
        if self.layer:
            self.layer.setOpacity(1)
            self.layer.triggerRepaint()
            
        self.canvas.refresh()
        self.dragging = False
        self.last_mouse_pos = None

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.pos()
            
            # If overlay doesn't exist, create it
            if not self.overlay:
                self.create_overlay()
            
            # Set line position based on direction and mouse position
            if self.swipe_direction in ["right", "left"]:
                self.overlay.set_split_position(event.pos().x())
            else:  # top, bottom
                self.overlay.set_split_position(event.pos().y())
            
            # Apply layer opacity based on direction
            self.update_layer_opacity()
            
            self.control_panel.update_status("🎯", f"Dragging - Layer Opacity: {int(self.layer_opacity * 100)}%")

    def canvasMoveEvent(self, event):
        if self.dragging and self.overlay:
            current_pos = event.pos()
            
            # Move line based on direction
            if self.swipe_direction in ["right", "left"]:
                self.overlay.set_split_position(current_pos.x())
            else:  # top, bottom
                self.overlay.set_split_position(current_pos.y())
            
            # Update layer opacity based on position
            self.update_layer_opacity_based_on_position(current_pos)
            
            self.canvas.refresh()
            self.last_mouse_pos = current_pos

    def update_layer_opacity_based_on_position(self, pos):
        """Update layer opacity based on mouse position and direction"""
        if not self.layer:
            return
            
        canvas_width = self.canvas.width()
        canvas_height = self.canvas.height()
        
        if self.swipe_direction == "right":
            # For right swipe: left of line shows layer with configured opacity, right shows full opacity
            if pos.x() <= 0:
                self.layer.setOpacity(1.0)  # Fully visible when line is at left edge
            elif pos.x() >= canvas_width:
                self.layer.setOpacity(self.layer_opacity)  # Configured opacity when line is at right edge
            else:
                # Gradual transition (optional - you can remove this for instant change)
                self.layer.setOpacity(self.layer_opacity)
                
        elif self.swipe_direction == "left":
            # For left swipe: right of line shows layer with configured opacity, left shows full opacity
            if pos.x() <= 0:
                self.layer.setOpacity(self.layer_opacity)  # Configured opacity when line is at left edge
            elif pos.x() >= canvas_width:
                self.layer.setOpacity(1.0)  # Fully visible when line is at right edge
            else:
                self.layer.setOpacity(self.layer_opacity)
                
        elif self.swipe_direction == "top":
            # For top swipe: below line shows layer with configured opacity, above shows full opacity
            if pos.y() <= 0:
                self.layer.setOpacity(1.0)  # Fully visible when line is at top edge
            elif pos.y() >= canvas_height:
                self.layer.setOpacity(self.layer_opacity)  # Configured opacity when line is at bottom edge
            else:
                self.layer.setOpacity(self.layer_opacity)
                
        elif self.swipe_direction == "bottom":
            # For bottom swipe: above line shows layer with configured opacity, below shows full opacity
            if pos.y() <= 0:
                self.layer.setOpacity(self.layer_opacity)  # Configured opacity when line is at top edge
            elif pos.y() >= canvas_height:
                self.layer.setOpacity(1.0)  # Fully visible when line is at bottom edge
            else:
                self.layer.setOpacity(self.layer_opacity)
            
        self.layer.triggerRepaint()

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.last_mouse_pos = None
            
            self.control_panel.update_status("🔄", f"Active - Layer Opacity: {int(self.layer_opacity * 100)}%")