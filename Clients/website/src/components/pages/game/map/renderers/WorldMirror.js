import { world_width } from "../map_const";

/**
 * Creates mirrored copies of a graphic for infinite horizontal scrolling
 * @param {PIXI.Graphics} graphic - The graphic to mirror
 * @returns {Array} Array of [left, middle, right] mirrored graphics
 */
export function createMirroredGraphics(graphic) {
    const left = graphic.clone();
    const middle = graphic.clone();
    const right = graphic.clone();
    
    left.x = -world_width;
    middle.x = 0;
    right.x = world_width;
    
    return [left, middle, right];
}
