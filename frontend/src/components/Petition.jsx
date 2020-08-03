import React, { useState, useEffect } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import "./css/Petition.css";

function Petition({ match }) {
  const petition_id = match.params.id;
  const [petition, setPetition] = useState({});

  useEffect(() => {
    fetchPetition();
  }, []);

  async function fetchPetition() {
    const params = { params: { id: petition_id } };
    try {
      let response = await axios.get(`/react/petition/get`, params);
      setPetition(response);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  return (
    <div className="About">
      <h1>Petition ID: {petition_id}</h1>
      <h2>Petition Data:</h2>
      <div>
        <div>{JSON.stringify(petition)}</div>
        {/* <JSONPretty id="json-pretty" data={petition}></JSONPretty> */}
      </div>
    </div>
  );
}

export default Petition;
