import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import PetitionList from "./PetitionList";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHome, faSearch } from "@fortawesome/free-solid-svg-icons";

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

  function renderSearchBar() {
    return (
      <div class="SearchBar">
        <input type="text" placeholder="Search Petitions..."></input>
        <FontAwesomeIcon icon={faSearch} />
      </div>
    );
  }

  return (
    <div>
      <div className="PetitionNav">
        <nav>
          <div>{renderSearchBar()}</div>
          <h2>State: {queryParams.state}</h2>

          <h3>Petitions Found: {numPetitionsFound.current}</h3>
        </nav>
      </div>
      <div>
        <PetitionList petitions={petitions}></PetitionList>
      </div>
    </div>
  );
}

export default PetitionNav;
