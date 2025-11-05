import {Box} from "@mui/material";
import {useEffect, useState, useCallback, useMemo} from "react";
import React from "react";
import {viewport} from "./map_app";
import {useViewport} from "./hooks/useViewport";
import {useSelectionMode} from "./hooks/useSelectionMode";
import {useDrawingMode} from "./hooks/useDrawingMode";
import {renderSelection, renderDrawings} from "./renderers/GraphicsRenderer";


export default function Map({provinces, countrys, teams, mode, selectionLevel, drawingLevel, fillColor, outlineColor, strokeWidth, drawings, setDrawings, finalDrawing, current_selection, setCurrentSelection}){
    const div_ref = React.createRef();
    // Global
    const [loaded, setLoaded] = useState(false)
    const [mousedown, setMousedown] = useState(false);

    // Selection
    const [selectPosition, setSelectPosition] = useState()

    // Drawing
    const [currentDrawing, setCurrentDrawing] = useState();
    const [drawPosition, setDrawPosition] = useState()

    // Initialize viewport using custom hook
    useViewport({ 
        divRef: div_ref, 
        provinces, 
        setLoaded, 
        setSelectPosition 
    });

    // Stop currentDrawing on Escape key
    const cancelDrawing = useCallback((event) => {
        if(event.key === "Escape" && currentDrawing){
            viewport.getChildByName("drawing_graphic").clear()
            viewport.getChildByName("drawing_info").text = ""
            setCurrentDrawing()
        }
    }, [currentDrawing])

    useEffect(() => {
        window.addEventListener("keydown", cancelDrawing)
        return () => window.removeEventListener("keydown", cancelDrawing)
    }, [cancelDrawing])

    // Only if Mode changes Mouse-buttons for dragging need to be changed
    useEffect(()=> {
        if (mode === 0 || mode === 2) viewport.drag({mouseButtons: "right"})
        if (mode === 1) {
            viewport.drag({mouseButtons: "all"})
            setCurrentSelection([])
        }
    }, [mode, setCurrentSelection])

    // Use selection mode hook
    useSelectionMode({
        mode,
        provinces,
        countrys,
        teams,
        selectionLevel,
        currentSelection: current_selection,
        setCurrentSelection,
        selectPosition,
        setSelectPosition,
        mousedown,
        setMousedown
    });

    // Use drawing mode hook
    useDrawingMode({
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
    });

    // Draw Current Selection using renderer
    useEffect(() => {
        let selection_container = viewport.getChildByName("selection_container")
        if (selection_container) {
            renderSelection(selection_container, current_selection)
        }
    }, [current_selection])


    // Reset Current Drawing if DrawingLevel changes
    useEffect(() => {
        setCurrentDrawing()
        const drawing_graphic = viewport.getChildByName("drawing_graphic")
        const drawing_info = viewport.getChildByName("drawing_info")
        if (drawing_graphic) drawing_graphic.clear()
        if (drawing_info) drawing_info.text = ""
    }, [mode, drawingLevel])

    // Draw all finished Drawings using renderer
    useEffect(() => {
        let drawings_container = viewport.getChildByName("drawings_container")
        if (drawings_container) {
            renderDrawings(drawings_container, drawings)
        }
    }, [drawings])


    return (
        <Box style={{width: "100%", height:"calc(100vh - 65px)", overflow: "hidden"}} ref={div_ref}/>
    )
}