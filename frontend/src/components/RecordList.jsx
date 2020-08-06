import React, { useState, useEffect } from "react";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import "./css/RecordList.css";

function RecordList({ match }) {
  const petition_id = match.params.petition_id;
  const [petition, setPetition] = useState({});
  const [records, setRecords] = useState([]);

  useEffect(() => {
    fetchRecords();
  }, []);

  async function fetchRecords() {
    try {
      let response = await axios.get(`/petition/${petition_id}/records`);
      const data = response["data"];
      setRecords(data["records"]);
      setPetition(data["petition"]);
    } catch (error) {
      // handle application not reachable
      console.log("error:", error);
    }
  }

  return (
    <div className="Record">
      <div>
        <h1>Petition ID: {petition_id}:</h1>
        <JSONPretty id="json-pretty" data={petition}></JSONPretty>
      </div>

      <br></br>
      <div>--------------------------</div>
      <br></br>

      <div>
        <h1>Records:</h1>
        <JSONPretty id="json-pretty" data={records}></JSONPretty>
      </div>
    </div>
  );
}

export default RecordList;
