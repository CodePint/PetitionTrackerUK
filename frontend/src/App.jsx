import React from "react";
import { BrowserRouter as Router, Switch, Route, Redirect } from "react-router-dom";
import NavBar from "./components/NavBar";
import Home from "./components/Home";
import About from "./components/About";
import Petition from "./components/Petition";
import PetitionList from "./components/PetitionList";
import RouteNotFound from "./components/RouteNotFound";

function App() {
  return (
    <Router>
      <div className="App">
        <NavBar />
        <div className="content">
          <Switch>
            <Route path="/" exact component={Home} />
            <Route path="/about" component={About} />
            <Route path="/petitions/:state?" exact component={PetitionList} />
            <Route path="/petition/:petition_id(\d+)" exact component={Petition} />
            <Route path="*" component={RouteNotFound} />
          </Switch>
        </div>
      </div>
    </Router>
  );
}

export default App;
