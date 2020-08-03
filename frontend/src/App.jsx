import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Switch, Route } from "react-router-dom";
import "./App.css";
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
            <Route path="/petitions" component={PetitionList} />
            <Route path="/petition/:id" component={Petition} />
            <Route path="*" component={RouteNotFound} />
          </Switch>
        </div>
        <footer className="Flask-Status">
          <div>Flask - React</div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
