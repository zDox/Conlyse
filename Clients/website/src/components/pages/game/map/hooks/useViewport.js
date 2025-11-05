import { useEffect, useCallback } from "react";
import * as PIXI from "pixi.js";
import { SmoothGraphics as Graphics } from '@pixi/graphics-smooth';
import { map_app, viewport } from "../map_app";
import { getGraphics } from "../drawing";
import { world_width, world_height, defaultTextStyle } from "../map_const";

/**
 * Custom hook to manage viewport initialization and lifecycle
 * @param {Object} params - Hook parameters
 * @param {React.RefObject} params.divRef - Reference to the div element
 * @param {Array} params.provinces - List of provinces
 * @param {Function} params.setLoaded - Setter for loaded state
 * @param {Function} params.setSelectPosition - Setter for select position
 * @returns {Function} resize - Function to resize the canvas
 */
export function useViewport({ divRef, provinces, setLoaded, setSelectPosition }) {
    const resize = useCallback(() => {
        map_app.renderer.resize(window.innerWidth, window.innerHeight);
    }, []);

    useEffect(() => {
        if (divRef.current) {
            divRef.current.appendChild(map_app.view);
            map_app.start();
            
            // Create mirrored world graphics
            let left = getGraphics(provinces);
            let middle = new PIXI.Graphics(left.geometry);
            let right = new PIXI.Graphics(left.geometry);
            middle.x = world_width;
            right.x = world_width * 2;
            
            // Create UI elements
            const selectRect = new Graphics();
            selectRect.name = "selectRect";
            
            const selection_container = new PIXI.Container();
            selection_container.name = "selection_container";
            
            const drawings_container = new PIXI.Container();
            drawings_container.name = "drawings_container";
            
            const drawing_graphic = new Graphics();
            drawing_graphic.name = "drawing_graphic";
            
            const drawing_info = new PIXI.Text("Test", defaultTextStyle);
            drawing_info.name = "drawing_info";
            
            viewport.addChild(left, middle, right, selection_container, drawings_container, drawing_graphic, drawing_info, selectRect);
            
            // Reset Selection if pointer leaves window
            viewport.on("pointerout", () => setSelectPosition());
            
            // Resets Viewport to enable infinite scrolling
            viewport.on("moved-end", event => {
                if (event.right < world_width) {
                    viewport.right += world_width;
                } else if (event.left > world_width * 2) {
                    viewport.left -= world_width;
                }
            });
            
            resize();
            map_app.stage.addChild(viewport);
            viewport.fit();
            viewport.moveCenter(world_width * 1.5, world_height / 2);
            setLoaded(true);
        }
        
        return () => {
            viewport.removeChildren(0, viewport.children.length - 1);
            map_app.stop();
        };
    }, [divRef, provinces, setLoaded, setSelectPosition, resize]);

    // Window resize handler
    useEffect(() => {
        window.addEventListener("resize", resize);
        return () => window.removeEventListener("resize", resize);
    }, [resize]);

    return resize;
}
