import {BrowserRouter as Router, Routes, Route} from "react-router-dom";
import Game from "./components/pages/game/game";
import Startpage from "./components/pages/Startpage";
import Dashboard from "./components/pages/game/dashboard";
import Country from "./components/pages/game/country";
import Countrys from "./components/pages/game/countrys";
import React from "react";
import {theme} from "./helper/theme";
import {CssBaseline, ThemeProvider} from "@mui/material";

import {QueryClientProvider, QueryClient} from "react-query";
import Provinces from "./components/pages/game/provinces";
import MapPage from "./components/pages/game/map/MapPage";
const queryClient = new QueryClient({
    defaultOptions: {
        queries:{
            cacheTime: 10 * 60 * 1000,
            refetchOnWindowFocus: false,
            refetchOnMount: false,
        }
    }
});

const App = () => {
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline/>
            <Router>
                <div className="App">
                    <QueryClientProvider client={queryClient}>
                        <Routes>
                            <Route path={"/game/:game_id"} element={<Game/>} exact/>
                            <Route path={"/game/:game_id/dashboard"} element={<Dashboard/>}/>
                            <Route path={"/game/:game_id/countrys"} element={<Countrys/>}/>
                            <Route path={"/game/:game_id/country/:country_id"} element={<Country/>}/>
                            <Route path={"/game/:game_id/provinces"} element={<Provinces/>}/>
                            <Route path={"/game/:game_id/map"} element={<MapPage/>}/>
                            <Route path={"/"} element={<Startpage/>} exact/>
                        </Routes>
                    </QueryClientProvider>

                </div>
            </Router>
        </ThemeProvider>
        );
}
export default App

