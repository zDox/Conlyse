import {useParams} from "react-router-dom";
import {useQueries, useQuery} from "react-query";
import * as api from "../../../../helper/api";
import Map from "./map";
import {get_combined_province} from "../../../../helper/provinces/provinces_getter";
import CustomDrawer from "../../../CustomDrawer";
import React, {useState} from "react";
import EditorMenu from "./EditorMenu";
import DetailedInformation from "./Modes/selectionMode/detailed_information";
import * as PIXI from "pixi.js";
import {pushDrawing} from "./Modes/drawingMode/drawing_mode";
import {defaultFillColour, defaultOutlineColour, defaultStrokeWidth} from "./map_const";
import DrawingsEditor from "./Modes/drawingMode/drawings_editor";

export default function MapPage(){
    const {game_id} = useParams()
    const {data} = useQuery(["game", game_id], () => api.get_game(game_id), {keepPreviousData : true});

    // Global
    const [mode, setMode] = useState(2)

    // Selection
    const [selectionLevel, setSelectionLevel] = useState(0)
    const [current_selection, setCurrentSelection] = useState([]);

    // Drawing
    const [drawings, setDrawings] = useState([])
    const [finalDrawing, setFinalDrawing] = useState()
    const [drawingLevel, setDrawingLevel] = useState(0)
    const [fillColor, setFillColor] = useState(defaultFillColour)
    const [outlineColor, setOutlineColor] = useState(defaultOutlineColour)
    const [strokeWidth, setStrokeWidth] = useState(defaultStrokeWidth)

    // Push current Selection to Drawings function
    let pushSelection = () => {
        let polygons = Object.values(current_selection).map(cs => new PIXI.Polygon(cs["points"]))
        if(current_selection.length !== 0){
            setDrawings(pushDrawing(drawings, -1, fillColor, outlineColor, strokeWidth, polygons))
            // after Push set selection to nothing
            setCurrentSelection([])
        }
    }

    // Push current finalDrawing to Drawings function
    let pushFinalDrawing = () => {
        if(finalDrawing){
            setDrawings(pushDrawing(drawings, -1, fillColor, outlineColor, strokeWidth, finalDrawing))
        }
        setFinalDrawing()
    }

    let defined = data ? data[game_id] : undefined;
    let game = {};

    if(!!defined){
        game = data[game_id]
    }
    let results = useQueries([
        { queryKey: ['static', "province", game["mid"]], queryFn: () => api.get_static_provinces(game["mid"]), keepPreviousData : true, enabled: !!defined},
        { queryKey: ['provinces', game["gid"], "list", game["ct"]], queryFn: () => api.get_provinces(game["gid"], "list", game["ct"]),  enabled: !!defined},
        { queryKey: ['countrys', game["gid"], "normal", "-1", "0", "0"], queryFn: () => api.get_countrys(game["gid"], "normal", "-1", "0", "0"), enabled: !!defined},
        { queryKey: ['teams', game.gid], queryFn: () => api.get_teams(game.gid), enabled: !!defined},
    ])
    let provinces = get_combined_province(results[1]["data"], results[0]["data"])
    const isSuccess = !results.some((result) => !result.isSuccess)
    console.log(provinces)

    if (!isSuccess) return <div>Loading</div>

    return(
        <CustomDrawer game_id={game_id}>
            <Map provinces={provinces}
                 countrys={results[2]["data"]}
                 teams={results[3]["data"]}

                 mode={mode} setMode={setMode}
                 selectionLevel={selectionLevel} setSelectionLevel={setSelectionLevel}
                 pushSelection={pushSelection}
                 drawingLevel={drawingLevel} setDrawingLevel={setDrawingLevel}
                 fillColor={fillColor} setFillColor={setFillColor}
                 outlineColor={outlineColor} setOutlineColor={setOutlineColor}
                 strokeWidth={strokeWidth}

                 drawings={drawings} setDrawings={setDrawings}
                 finalDrawing={finalDrawing} setFinalDrawing={setFinalDrawing}
                 current_selection={current_selection}
                 setCurrentSelection={setCurrentSelection}
            />
            <EditorMenu mode={mode} setMode={setMode}
                        selectionLevel={selectionLevel} setSelectionLevel={setSelectionLevel}
                        pushSelection={pushSelection}
                        drawingLevel={drawingLevel} setDrawingLevel={setDrawingLevel}
                        fillColor={fillColor} setFillColor={setFillColor}
                        outlineColor={outlineColor} setOutlineColor={setOutlineColor}
                        finalDrawing={finalDrawing} pushFinalDrawing={pushFinalDrawing}
                        strokeWidth={strokeWidth} setStrokeWidth={setStrokeWidth}
            />
            {mode === 0 ? <DetailedInformation countrys={results[2]["data"]} current_province={current_selection} setCurrentProvince={setCurrentSelection}/> : undefined}
            {mode === 2 ? <DrawingsEditor drawings={drawings} setDrawings={setDrawings} /> : undefined}
        </CustomDrawer>
    )
}