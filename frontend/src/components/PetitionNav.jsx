import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import PetitionList from "./PetitionList";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHome, faSearch } from "@fortawesome/free-solid-svg-icons";
import { BrowserRouter as Router, Link, Redirect } from "react-router-dom";

// import "../styles/PetitionNav.css";

function PetitionNav() {
  const [queryParams, setQueryParams] = useState(baseQuery());
  const numPetitionsFound = useRef(0);
  const [petitions, setPetitions] = useState({});
  const queryResult = useRef(null);

  function baseQuery() {
    return {
      state: "open",
      items: 20,
    };
  }

  useEffect(() => {
    queryPetitions();
  }, []);

  async function queryPetitions() {
    const params = { params: queryParams };
    try {
      let response = await axios.get("/petitions", params);
      let data = response.data;
      queryResult.current = data;
      if (data.petitions && data.petitions.length > 0) {
        numPetitionsFound.current = data.meta.items.total;
        setPetitions(data.petitions);
      }
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  const handlePetitionSearchForm = (event) => {
    event.preventDefault();
    // debugger;
  };

  function renderSearchBar() {
    return (
      <div class="searchBar">
        <input type="text" name="query" placeholder="Search Petitions..."></input>
        <button type="submit">
          {" "}
          <FontAwesomeIcon icon={faSearch} />
        </button>
      </div>
    );
  }

  function renderToggle() {
    return (
      <div class="toggle">
        <ul>
          <li>Popular</li>
          <li>Open</li>
          <li>New</li>
        </ul>
      </div>
    );
  }

  return (
    <div>
      <div className="PetitionNav">
        <nav>
          <form onSubmit={handlePetitionSearchForm}>
            <div>{renderSearchBar()}</div>

            <div>{renderToggle()}</div>
          </form>
        </nav>
        <div className="results">
          <h5>{numPetitionsFound.current} petitions</h5>
        </div>
        <div>
          <PetitionList petitions={petitions}></PetitionList>
        </div>
      </div>
    </div>
  );
}

export default PetitionNav;
