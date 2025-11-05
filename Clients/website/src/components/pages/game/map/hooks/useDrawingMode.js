import { useEffect, useCallback } from "react";
import { viewport } from "../map_app";
import { pushDrawing } from "../Modes/drawingMode/drawing_mode";
import { LINE_SCALE_MODE } from '@pixi/graphics-smooth';
import * as PIXI from "pixi.js";

/**
 * Custom hook to manage drawing mode event handlers
 * @param {Object} params - Hook parameters
 * @param {number} params.mode - Current mode (2 for drawing)
 * @param {number} params.drawingLevel - Drawing level (0: pencil, 1: line, 2: circle)
 * @param {Array} params.fillColor - Fill color [color, alpha]
 * @param {Array} params.outlineColor - Outline color [color, alpha]
 * @param {number} params.strokeWidth - Stroke width
 * @param {Array} params.drawings - List of drawings
 * @param {Function} params.setDrawings - Setter for drawings
 * @param {Object} params.currentDrawing - Current drawing in progress
 * @param {Function} params.setCurrentDrawing - Setter for current drawing
 * @param {Object} params.drawPosition - Draw position
 * @param {Function} params.setDrawPosition - Setter for draw position
 * @param {boolean} params.mousedown - Mouse down state
 */
export function useDrawingMode({
    mode,
    drawingLevel,
    fillColor,
    outlineColor,
    strokeWidth,
    drawings,
    setDrawings,
    currentDrawing,
    setCurrentDrawing,
    drawPosition,
    setDrawPosition,
    mousedown
}) {
    // Handle mouse down for drawing
    const handleLineSet = useCallback((event) => {
        if (mode === 2) {
            let pos = event.data.getLocalPosition(viewport);
            let drawing_graphic = viewport.getChildByName("drawing_graphic");
            let drawing_info = viewport.getChildByName("drawing_info");
            drawing_info.text = "";
            drawing_graphic.clear();
            
            if (drawingLevel === 0) {
                drawing_graphic.lineStyle({ color: fillColor[0], alpha: fillColor[1], width: strokeWidth });
                setCurrentDrawing([pos]);
                setDrawPosition(pos);
            } else if (drawingLevel === 1) {
                if (currentDrawing) {
                    setDrawings(pushDrawing(drawings, drawingLevel, fillColor, fillColor, strokeWidth, { ...currentDrawing, "x2": pos.x, "y2": pos.y }));
                    setCurrentDrawing();
                } else {
                    setCurrentDrawing({ "x1": pos.x, "y1": pos.y });
                }
            } else if (drawingLevel === 2) {
                if (currentDrawing) {
                    let r = Math.round(Math.hypot(Math.abs(pos.x - currentDrawing["x"]), Math.abs(pos.y - currentDrawing["y"])));
                    setDrawings(pushDrawing(drawings, drawingLevel, fillColor, outlineColor, strokeWidth, { ...currentDrawing, "r": r }));
                    setCurrentDrawing();
                } else {
                    setCurrentDrawing({ "x": pos.x, "y": pos.y });
                }
            }
        }
    }, [mode, drawingLevel, currentDrawing, fillColor, outlineColor, strokeWidth, drawings, setDrawings, setCurrentDrawing, setDrawPosition]);

    useEffect(() => {
        viewport.on("mousedown", handleLineSet);
        return () => viewport.removeListener("mousedown", handleLineSet);
    }, [handleLineSet]);

    // Handle mouse up for pencil drawing
    const handlePencilSet = useCallback(() => {
        if (mode === 2 && drawingLevel === 0) {
            if (currentDrawing && currentDrawing.length >= 2) {
                let drawing_graphic = viewport.getChildByName("drawing_graphic");
                drawing_graphic.clear();
                setDrawings(pushDrawing(drawings, drawingLevel, fillColor, fillColor, strokeWidth, currentDrawing));
            }
        }
    }, [mode, drawingLevel, currentDrawing, fillColor, strokeWidth, drawings, setDrawings]);

    useEffect(() => {
        viewport.addListener("mouseup", handlePencilSet);
        return () => viewport.removeListener("mouseup", handlePencilSet);
    }, [handlePencilSet]);

    // Handle mouse move for drawing
    const handleDrawingMove = useCallback((event) => {
        let drawing_graphic = viewport.getChildByName("drawing_graphic");
        let drawing_info = viewport.getChildByName("drawing_info");
        
        if (mode === 2) {
            if (drawingLevel === 0 && mousedown && currentDrawing) {
                let pos = event.data.getLocalPosition(viewport);
                if (Math.hypot(Math.abs(pos.x - drawPosition.x), Math.abs(pos.y - drawPosition.y)) > strokeWidth * 0.3) {
                    drawing_graphic.moveTo(drawPosition.x, drawPosition.y);
                    drawing_graphic.lineTo(pos.x, pos.y);
                    setDrawPosition(pos);
                    let cp = [...currentDrawing];
                    cp.push(pos);
                    setCurrentDrawing(cp);
                }
            } else if (drawingLevel === 1 && currentDrawing) {
                let pos = event.data.getLocalPosition(viewport);
                drawing_info.position = new PIXI.Point(pos.x + 30, pos.y + 20);
                drawing_info.text = Math.round(Math.hypot(Math.abs(pos.x - currentDrawing["x1"]), Math.abs(pos.y - currentDrawing["y1"]))).toString();
                drawing_graphic.clear();
                drawing_graphic.lineStyle({ color: fillColor[0], alpha: fillColor[1], width: strokeWidth, scaleMode: LINE_SCALE_MODE.NORMAL });
                drawing_graphic.moveTo(currentDrawing["x1"], currentDrawing["y1"]);
                drawing_graphic.lineTo(pos.x, pos.y);
            } else if (drawingLevel === 2 && currentDrawing) {
                let pos = event.data.getLocalPosition(viewport);
                let r = Math.hypot(Math.abs(pos.x - currentDrawing["x"]), Math.abs(pos.y - currentDrawing["y"]));
                drawing_info.position = new PIXI.Point(pos.x + 30, pos.y + 20);
                drawing_info.text = Math.round(r).toString(10);
                drawing_graphic.clear();
                drawing_graphic.beginFill(fillColor[0], fillColor[1]);
                drawing_graphic.lineStyle({ color: outlineColor[0], alpha: outlineColor[1], width: strokeWidth, scaleMode: LINE_SCALE_MODE.NORMAL });
                drawing_graphic.drawCircle(currentDrawing["x"], currentDrawing["y"], r);
                drawing_graphic.endFill();
            }
        }
    }, [mode, mousedown, currentDrawing, drawPosition, drawingLevel, fillColor, outlineColor, strokeWidth, setDrawPosition, setCurrentDrawing]);

    useEffect(() => {
        viewport.on("mousemove", handleDrawingMove);
        return () => viewport.removeListener("mousemove", handleDrawingMove);
    }, [handleDrawingMove]);
}
