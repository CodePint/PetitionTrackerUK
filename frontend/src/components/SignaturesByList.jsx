import React, { useState, useEffect } from "react";
import _ from "lodash";
import axios from "axios";
import JSONPretty from "react-json-pretty";
import "./css/SignaturesByList.css";

function SignaturesByList({ match }) {
  const petition_id = match.params.petition_id;
  const record_id = match.params.record_id;
  const geography = match.params.geography;

  const [petition, setPetition] = useState({});
  const [record, setRecord] = useState({});
  const [signaturesBy, setSignaturesBy] = useState({});

  useEffect(() => {
    fetchRecord();
  }, []);

  async function fetchRecord() {
    try {
      let response = await axios.get(
        `/petition/${petition_id}/record/${record_id}/signatures/${geography}`
      );
      const data = response["data"];
      setRecord(data["record"]);
      setPetition(data["petition"]);
      setSignaturesBy(data["signatures"]);
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
        <h1>Record ID: {record_id}</h1>
        <JSONPretty id="json-pretty" data={record}></JSONPretty>
      </div>

      <br></br>
      <div>--------------------------</div>
      <br></br>

      <div>
        <h1>Signatures By: {_.capitalize(geography)}</h1>
        <JSONPretty id="json-pretty" data={signaturesBy}></JSONPretty>
      </div>
    </div>
  );
}

export default SignaturesByList;
