import * as PIXI from "pixi.js";
import { selectionLockedColour, world_width } from "../map_const";

/**
 * Renders the current selection on the viewport
 * @param {PIXI.Container} container - The selection container
 * @param {Array} currentSelection - Array of selected provinces
 */
export function renderSelection(container, currentSelection) {
    container.removeChildren();
    let selection_graphic = new PIXI.Graphics();
    
    for (let province in currentSelection) {
        province = currentSelection[province];
        let polygon = new PIXI.Polygon(province["points"]);
        selection_graphic.beginFill(selectionLockedColour[0], selectionLockedColour[1]);
        selection_graphic.drawPolygon(polygon);
        selection_graphic.endFill();
    }
    
    // Create mirrored copies for infinite scrolling
    let middle = selection_graphic.clone();
    let right = selection_graphic.clone();
    middle.x = world_width;
    right.x = world_width * 2;
    container.addChild(selection_graphic, middle, right);
}

/**
 * Renders all drawings on the viewport
 * @param {PIXI.Container} container - The drawings container
 * @param {Array} drawings - Array of drawing objects
 */
export function renderDrawings(container, drawings) {
    container.removeChildren();
    let drawings_graphic = new PIXI.Graphics();
    
    for (let drawing in drawings) {
        drawing = drawings[drawing];
        console.log(drawing);
        drawings_graphic.lineStyle({ width: drawing["strokeWidth"], color: drawing["outlineColor"][0], alpha: drawing["outlineColor"][1] });
        
        switch (drawing["drawingLevel"]) {
            case -1:
                for (let polygon in drawing["data"]) {
                    polygon = drawing["data"][polygon];
                    drawings_graphic.beginFill(drawing["fillColor"][0], drawing["fillColor"][1]);
                    drawings_graphic.drawPolygon(polygon);
                    drawings_graphic.endFill();
                }
                break;
            case 0:
                // Pencil
                let point = drawing["data"][0];
                drawings_graphic.moveTo(point.x, point.y);
                drawings_graphic.lineStyle({ width: drawing["strokeWidth"], color: drawing["outlineColor"][0], alpha: drawing["outlineColor"][1] });
                for (let key in drawing["data"]) {
                    let next_point = drawing["data"][parseInt(key) + 1];
                    if (next_point) {
                        drawings_graphic.lineTo(next_point.x, next_point.y);
                    }
                }
                break;
            case 1:
                // Line
                drawings_graphic.moveTo(drawing["data"]["x1"], drawing["data"]["y1"]);
                drawings_graphic.lineTo(drawing["data"]["x2"], drawing["data"]["y2"]);
                break;
            case 2:
                drawings_graphic.beginFill(drawing["fillColor"][0], drawing["fillColor"][1]);
                drawings_graphic.drawCircle(drawing["data"]["x"], drawing["data"]["y"], drawing["data"]["r"]);
                drawings_graphic.endFill();
                break;
        }
    }
    
    // Create mirrored copies for infinite scrolling
    let left = drawings_graphic.clone();
    let right = drawings_graphic.clone();
    left.x = -world_width;
    right.x = world_width;
    container.addChild(drawings_graphic, left, right);
}
