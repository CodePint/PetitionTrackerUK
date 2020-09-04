import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import PetitionList from "./PetitionList";
import "./css/PetitionListController.css";

function PetitionListController() {
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

  return (
    <div className="PetitionListController">
      <nav>
        <h2>State: {queryParams.state}</h2>
        <h3>Petitions Found: {numPetitionsFound.current}</h3>
      </nav>

      <PetitionList petitions={petitions}></PetitionList>
    </div>
  );
}

export default PetitionListController;
