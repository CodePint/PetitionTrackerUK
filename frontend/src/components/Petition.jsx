import React, { useState, useEffect } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import "./css/Petition.css";

function Petition({ match }) {
  const petition_id = match.params.petition_id;
  const [petition, setPetition] = useState({});
  const [latestRecord, setlatestRecord] = useState({});
  const [latestRecords, setLatestRecords] = useState({});

  useEffect(() => {
    fetchPetition();
  }, []);

  async function fetchPetition() {
    try {
      let response = await axios.get(`/petition/${petition_id}`);
      let data = response["data"];
      setPetition(data["petition"]);
      setlatestRecord(data["latest_record"]);
      setLatestRecords(data["records"]);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  return (
    <div className="Petition">
      <h1>Petition ID: {petition_id}</h1>
      <h2>Petition data:</h2>
      <div>
        <JSONPretty id="json-pretty" data={petition}></JSONPretty>
      </div>

      <h2>Latest Records ({latestRecords.length}):</h2>
      <div>
        <JSONPretty id="json-pretty" data={latestRecords}></JSONPretty>
      </div>

      <h2>Lastest Record:</h2>
      <div>
        <JSONPretty id="json-pretty" data={latestRecord}></JSONPretty>
      </div>
    </div>
  );
}

export default Petition;
