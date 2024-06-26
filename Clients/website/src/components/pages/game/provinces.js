import {useParams} from "react-router-dom";
import CustomDrawer from "../../CustomDrawer";
import {DataGrid, GridToolbar} from "@mui/x-data-grid";
import * as React from "react";
import {
    ArrowLeft,
    ArrowRightOutlined,


} from "@mui/icons-material";
import {getResourceName} from "../../../helper/game_types";
import {getDifference} from "../../../helper/time";
import {useState} from "react";
import {IconButton, LinearProgress, Stack, TextField} from "@mui/material";
import {theme} from "../../../helper/theme";
import getRows, {get_combined_province} from "../../../helper/provinces/provinces_getter";
import {useQueries, useQuery} from "react-query";
import * as api from "../../../helper/api";
import {getInterestingBuildingName} from "../../../helper/provinces/buildings_getter";
import {isEqual} from "lodash";


export default function Provinces() {
    const {game_id} = useParams()
    const {data} = useQuery(["game", game_id], () => api.get_game(game_id), {keepPreviousData : true});
    const [day, setDay] = useState(0)
    const [rows, setRows] = useState([])
    const [rows_loaded, setRows_loaded] = useState(false)
    const [loaded, setLoaded] = useState(false)
    const [columns, setColumns] = useState([
        { field: "plid", headerName: 'Province Location ID', hide: true, flex: 0.1},
        { field: "pn", headerName: 'Province Name', hide: false, flex: 0.2},
        { field: "cn", headerName: 'Country Name', hide: false, flex: 0.2},
        { field: "vp", headerName: "Victory Points", hide: false, flex: 0.15},
        { field: "ml", headerName: "Morale", hide: false, flex: 0.15},
        { field: "tc", headerName: "Total Cost", hide: false, flex: 0.15},
        { field: "1", headerName: getResourceName("1"),renderHeader: (params => {return getResourceName(params.field)}), flex: 0.08, hide:true},
        { field: "2", headerName: getResourceName("2"),renderHeader: (params => {return getResourceName(params.field)}), flex: 0.08, hide:true},
        { field: "4", headerName: getResourceName("4"),renderHeader: (params => {return getResourceName(params.field)}), flex: 0.08, hide:true},
        { field: "5", headerName: getResourceName("5"),renderHeader: (params => {return getResourceName(params.field)}), flex: 0.08, hide:true},
        { field: "6", headerName: getResourceName("6"),renderHeader: (params => {return getResourceName(params.field)}), flex: 0.08, hide:true},
        { field: "20", headerName: getResourceName("20"),renderHeader: (params => {return getResourceName(params.field)}), flex: 0.08, hide:true},
        { field: "b0", headerName: getInterestingBuildingName(0), hide: false},
        { field: "b1", headerName: getInterestingBuildingName(1), hide: false},
        { field: "b2", headerName: getInterestingBuildingName(2), hide: false},
        { field: "b3", headerName: getInterestingBuildingName(3), hide: false},
        { field: "b4", headerName: getInterestingBuildingName(4), hide: false, minWidth: 140},
        { field: "psid", headerName: "Province State ID", hide: true},
        { field: "tt", headerName: "Terrain Type", hide: true},
        { field: "rg", headerName: "Region ID", hide: true},
    ])
    let defined = data ? data[game_id] : undefined;
    let game = {};

    if(!!defined){
        game = data[game_id]
        if (!loaded){
            setDay(getDifference(game["st"], game["ct"], "D"))
            setLoaded(true)
        }
    }
    let timestamp = game["st"] + day*3600*24
    let results = useQueries([
        { queryKey: ['static', "province", game["mid"]], queryFn: () => api.get_static_provinces(game["mid"]), keepPreviousData : true, enabled: !!defined && loaded},
        { queryKey: ['provinces', game["gid"], "list", timestamp], queryFn: () => api.get_provinces(game["gid"], "list", timestamp),  enabled: !!defined && loaded},
        { queryKey: ['countrys', game["gid"], "normal", "-1", "0", "0"], queryFn: () => api.get_countrys(game["gid"], "normal", "-1", "0", "0"), enabled: !!defined},
        { queryKey: ['static_upgrades'], queryFn: api.get_static_upgrades},
    ])

    const isSuccess = !results.some(query => !query.isSuccess)
    const isFetching = results.some(query => query.isFetching)


    if(isSuccess && !rows_loaded) {
        setRows_loaded(true)
        setRows(getRows(Object.values(results[2]["data"]), get_combined_province(results[1]["data"], results[0]["data"]), results[3]["data"]))
    }
    const handleDayChange = (day) => {
        setRows_loaded(false)
        setDay(day)
    }

    return(
        <CustomDrawer game_id={game["gid"]}>
            <div style={{margin: 20}}>
                <div style={{height: "calc(100vh - 160px)", width: "100%"}}>
                    <Stack direction={"row"} justifyContent={"space-between"} alignItems={"flex-end"} mb={2}>
                        <Stack direction={"row"} height={40} spacing={1} sx={{
                            right:0
                        }}>
                            <IconButton sx={{
                                border: 1,
                                borderColor: theme.palette.primary.main,
                                height: 36,
                                width: 36,
                            }} variant={"outlined"}
                                        onClick={() => {
                                            if(day > 0){
                                                handleDayChange(day-1)
                                            }
                                        }}
                            >
                                <ArrowLeft color={"primary"}/>
                            </IconButton>
                            <TextField
                                type="text"
                                pattern="[0-9]*"
                                onKeyPress={(event) => {
                                    if (!/[0-9]/.test(event.key)) {
                                        event.preventDefault();
                                    }
                                }}
                                onInput={event => {
                                    if (event.target.value >= getDifference(game["st"], game["ct"], "D")){
                                        event.target.value = getDifference(game["st"], game["ct"], "D")
                                    }else if(event.target.value < 0){
                                        event.target.value = 0
                                    }
                                }}
                                onChange={(event) => {
                                    if (event.target.value === ""){
                                        if (parseInt(day) === 0){
                                            event.preventDefault()
                                            return
                                        }
                                        event.target.value = 0
                                    }
                                    if(event.target.value <= getDifference(game["st"], game["ct"], "D")){
                                        handleDayChange(parseInt(event.target.value))
                                    }else {
                                        event.preventDefault()
                                    }
                                }}
                                variant={"standard"}
                                margin={"none"}
                                size={"small"}
                                sx={{
                                    width: 35,
                                }}
                                value={day}
                            />
                            <IconButton variant={"outlined"} sx={{
                                border: 1,
                                borderColor: theme.palette.primary.main,
                                height: 36,
                                width: 36,
                            }}
                                        onClick={() => {
                                            if(day < getDifference(game["st"], game["ct"], "D")){
                                                handleDayChange(Number(day) + 1)
                                            }
                                        }}
                            >
                                <ArrowRightOutlined color={"primary"}/>
                            </IconButton>
                        </Stack>
                    </Stack>

                    <DataGrid
                        columns={columns}
                        rows={rows}
                        components={{ Toolbar: GridToolbar, LoadingOverlay: LinearProgress}}
                        onStateChange={
                            // Sets the State of the Columns otherwise day changes would make enabled columns visible or hidden again
                            (state) => {
                                let new_columns = columns
                                for (let column in state.columns.lookup){
                                    column = state.columns.lookup[column]
                                    new_columns.find((new_column) => column["field"] === new_column["field"])["hide"]= column["hide"]
                                }
                                if(!isEqual(columns, new_columns)) setColumns(new_columns)
                            }
                        }
                        loading={isFetching}
                        style={{
                            flexGrow: 1,
                        }}
                    />
                </div>
            </div>
        </CustomDrawer>
    )
}