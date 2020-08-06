import React, { useState, useEffect } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import "./css/Record.css";

function Record({ match }) {
  const record_id = match.params.record_id;
  const petition_id = match.params.petition_id;

  const [petition, setPetition] = useState({});
  const [record, setRecord] = useState({});

  useEffect(() => {
    fetchRecord();
  }, []);

  async function fetchRecord() {
    try {
      let response = await axios.get(
        `/petition/${petition_id}/record/${record_id}`
      );
      const data = response["data"];
      setRecord(data["record"]);
      setPetition(data["petition"]);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  return (
    <div className="Record">
      <div>
        <div>----Record Page----</div>
        <h1>Petition ID: {petition_id}:</h1>
        <JSONPretty id="json-pretty" data={petition}></JSONPretty>
      </div>

      <br></br>
      <div>--------------------------</div>
      <br></br>

      <div>
        <h1>Record ID: {record_id}:</h1>
        <JSONPretty id="json-pretty" data={record}></JSONPretty>
      </div>
    </div>
  );
}

export default Record;
