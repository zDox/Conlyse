import {Box, Grid, IconButton} from "@mui/material";
import ModeSwitch from "./components/ModeSwitch";
import SelectGroupButton from "./components/SelectGroupButton";
import {
    CircleOutlined,
    Edit,
    Flag,
    Group, HighlightAlt,
    LocationCity,
    PolylineOutlined,
    RemoveOutlined
} from "@mui/icons-material";
import ColorsSelector from "./Modes/drawingMode/colors_selector";
import StrokeWidthSelector from "./Modes/drawingMode/stroke_width_selector";

export default function EditorMenu({mode, setMode, selectionLevel, setSelectionLevel, pushSelection, pushFinalDrawing, drawingLevel, setDrawingLevel, fillColor, setFillColor, outlineColor, setOutlineColor, finalDrawing, strokeWidth, setStrokeWidth}){
    return (
        <Box sx={{
            position: "absolute",
            left: 0,
            top: 65,
            margin: 2,
            backgroundColor: "background.paper",
            border: 3,
            borderColor: "primary.main",
            borderRadius: 10,
        }}>
            <Grid container
                  columnSpacing={3}
                  direction={"row"}
                  alignItems={"center"}
                  m={1}
            >
                <Grid item >
                    <ModeSwitch mode={mode} setMode={setMode}/>
                </Grid>
                <Grid item >
                    {mode === 0 ? <SelectGroupButton categories={[<LocationCity/>, <Flag/>, <Group/>]}
                                                     select={selectionLevel}
                                                     setSelect={setSelectionLevel}/>
                        : undefined}
                    {mode === 2 ? <SelectGroupButton categories={[<Edit/>, <RemoveOutlined sx={{transform: "rotate(-45deg)"}}/> ,<CircleOutlined/>, <PolylineOutlined/>]}
                                                     select={drawingLevel}
                                                     setSelect={setDrawingLevel}/>
                        : undefined}
                </Grid>
                <Grid item >
                    {mode === 0 ? <IconButton onClick={pushSelection}><HighlightAlt/></IconButton> : undefined}
                    {mode === 2 ? <ColorsSelector fillColor={fillColor} setFillColor={setFillColor}
                                                  outlineColor={outlineColor} setOutlineColor={setOutlineColor}/>
                        : undefined}
                </Grid>
                <Grid item>
                    {mode === 2 && finalDrawing ? <IconButton onClick={pushFinalDrawing}><HighlightAlt/></IconButton> : undefined}
                </Grid>
                <Grid item>
                    {mode === 2 ? <StrokeWidthSelector strokeWidth={strokeWidth} setStrokeWidth={setStrokeWidth}/> : undefined}
                </Grid>
            </Grid>
        </Box>
    )
}