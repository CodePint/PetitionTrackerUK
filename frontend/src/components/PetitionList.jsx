import React, { useState, useEffect } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import "./css/PetitionList.css";

function PetitionList({ match }) {
  const [queryState, setQueryState] = useState("all");
  const [petitionList, setPetitionList] = useState([]);

  useEffect(() => {
    fetchPetitionList();
  }, []);

  async function fetchPetitionList() {
    const params = { params: { state: JSON.stringify(queryState) } };
    try {
      let response = await axios.get("/petitions", params);
      setPetitionList(response["data"]["petitions"]);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  return (
    <div className="PetitionList">
      <h1>Petition List</h1>
      <h2>QueryState: {queryState}</h2>
      <div>
        <JSONPretty id="json-pretty" data={petitionList}></JSONPretty>
      </div>
    </div>
  );
}

export default PetitionList;
