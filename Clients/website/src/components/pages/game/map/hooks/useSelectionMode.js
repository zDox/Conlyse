import { useEffect, useCallback } from "react";
import { viewport } from "../map_app";
import { handleSelection } from "../Modes/selectionMode/selection_mode";
import { selectionColour } from "../map_const";

/**
 * Custom hook to manage selection mode event handlers
 * @param {Object} params - Hook parameters
 * @param {number} params.mode - Current mode (0 for selection)
 * @param {Array} params.provinces - List of provinces
 * @param {Array} params.countrys - List of countries
 * @param {Array} params.teams - List of teams
 * @param {number} params.selectionLevel - Selection level (0: province, 1: country, 2: team)
 * @param {Array} params.currentSelection - Current selection
 * @param {Function} params.setCurrentSelection - Setter for current selection
 * @param {Object} params.selectPosition - Select position
 * @param {Function} params.setSelectPosition - Setter for select position
 * @param {boolean} params.mousedown - Mouse down state
 * @param {Function} params.setMousedown - Setter for mouse down state
 */
export function useSelectionMode({
    mode,
    provinces,
    countrys,
    teams,
    selectionLevel,
    currentSelection,
    setCurrentSelection,
    selectPosition,
    setSelectPosition,
    mousedown,
    setMousedown
}) {
    // Handle mouse down to start selection
    const handleSetSelectionPosition = useCallback((event) => {
        setMousedown(true);
        if (mode === 0) setSelectPosition(event.data.getLocalPosition(viewport));
    }, [mode, setMousedown, setSelectPosition]);

    useEffect(() => {
        viewport.on("mousedown", handleSetSelectionPosition);
        return () => viewport.removeListener("mousedown", handleSetSelectionPosition);
    }, [handleSetSelectionPosition]);

    // Handle mouse up to complete selection
    const handleSetSelection = useCallback((event) => {
        setMousedown(false);
        let pos = event.data.getLocalPosition(viewport);
        if (!!selectPosition && mode === 0) {
            if (Math.hypot(Math.abs(pos.x - selectPosition.x), Math.abs(pos.y - selectPosition.y)) < viewport.threshold) {
                setCurrentSelection(handleSelection(provinces, countrys, teams, [pos], currentSelection, selectionLevel, event.data.originalEvent.shiftKey));
            } else {
                setCurrentSelection(handleSelection(provinces, countrys, teams, [pos, selectPosition], currentSelection, selectionLevel, event.data.originalEvent.shiftKey));
            }
        }
        setSelectPosition();
        let selectRect = viewport.getChildByName("selectRect");
        selectRect.clear();
    }, [mode, selectPosition, currentSelection, selectionLevel, provinces, countrys, teams, setMousedown, setCurrentSelection, setSelectPosition]);

    useEffect(() => {
        viewport.on("mouseup", handleSetSelection);
        return () => viewport.removeListener("mouseup", handleSetSelection);
    }, [handleSetSelection]);

    // Handle mouse move to draw selection rectangle
    const handleSelectionMove = useCallback((event) => {
        let selectRect = viewport.getChildByName("selectRect");
        if (!!selectPosition && mode === 0) {
            let pos = event.data.getLocalPosition(viewport);
            selectRect.clear();
            selectRect.beginFill(selectionColour[0], selectionColour[1]);
            selectRect.drawRect(
                Math.min(pos.x, selectPosition.x),
                Math.min(pos.y, selectPosition.y),
                Math.max(pos.x, selectPosition.x) - Math.min(pos.x, selectPosition.x),
                Math.max(pos.y, selectPosition.y) - Math.min(pos.y, selectPosition.y),
            );
            selectRect.endFill();
        }
    }, [mode, selectPosition]);

    useEffect(() => {
        viewport.on("mousemove", handleSelectionMove);
        return () => viewport.removeListener("mousemove", handleSelectionMove);
    }, [handleSelectionMove]);
}
