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

/**
 * Creates three copies of a graphic at positions for infinite scrolling
 * Positioned at (0, world_width, world_width*2)
 * @param {PIXI.Graphics} graphic - The graphic to copy
 * @returns {Object} Object with left, middle, right properties
 */
export function createWorldCopies(graphic) {
    const middle = graphic.clone();
    const right = graphic.clone();
    
    middle.x = world_width;
    right.x = world_width * 2;
    
    return { left: graphic, middle, right };
}

/**
 * Adds mirrored graphics to a container
 * Positions graphics at (-world_width, 0, world_width)
 * @param {PIXI.Container} container - The container to add graphics to
 * @param {PIXI.Graphics} graphic - The graphic to mirror and add
 */
export function addMirroredToContainer(container, graphic) {
    const [left, middle, right] = createMirroredGraphics(graphic);
    container.addChild(left, middle, right);
}
