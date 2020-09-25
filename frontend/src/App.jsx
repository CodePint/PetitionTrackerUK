import React from "react";
import { BrowserRouter as Router, Switch, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import Home from "./components/Home";
import About from "./components/About";
import Petition from "./components/Petition";
import PetitionList from "./components/PetitionList";
import Route404 from "./components/errors/Route404";
import Petition404 from "./components/errors/Petition404";
import Ping from "./components/utils/Ping";

function App() {
  return (
    <Router>
      <div className="App">
        <NavBar />
        <div className="content">
          <Switch>
            <Route path="/" exact component={Home} />
            <Route path="/about" component={About} />
            <Route path="/ping" exact component={Ping} />
            <Route path="/petitions/:state?" exact component={PetitionList} />
            <Route path="/petition/:petition_id(\d+)" exact component={Petition} />
            <Route path="/petition/error/404/:petition_id" exact component={Petition404} />
            <Route path="*" component={Route404} />
          </Switch>
        </div>
      </div>
    </Router>
  );
}

export default App;
