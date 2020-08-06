import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Switch, Route } from "react-router-dom";
import "./App.css";
import NavBar from "./components/NavBar";
import Home from "./components/Home";
import About from "./components/About";
import Petition from "./components/Petition";
import PetitionList from "./components/PetitionList";
import Record from "./components/Record";
import RecordList from "./components/RecordList";

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
            <Route path="/petition/:id(\d+)" exact component={Petition} />
            <Route
              path="/petition/:petition_id(\d+)/record/:record_id(\d+)"
              exact
              component={Record}
            />
            <Route
              path="/petitions/list/:state?"
              exact
              component={PetitionList}
            />
            <Route
              path="/petition/records/list/:id(\d+)"
              exact
              component={RecordList}
            />
            |
            <Route path="*" component={RouteNotFound} />
          </Switch>
          <footer className="Flask-Status">
            <div>Flask - React</div>
          </footer>
        </div>
      </div>
    </Router>
  );
}

export default App;
