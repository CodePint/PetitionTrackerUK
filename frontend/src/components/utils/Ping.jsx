import React, { useState, useEffect } from "react";
import axios from "axios";

function Ping({ match }) {
  const sender = match.params.sender;
  const API_URL_PREFIX = process.env.REACT_APP_FLASK_API_URL_PREFIX || "";
  const [data, setData] = useState({});

  useEffect(() => {
    pingAPI();
  }, []);

  async function pingAPI() {
    console.log("pinging API!");
    try {
      let response = await axios.get(`${API_URL_PREFIX}/ping`);
      let result = response.data.response;
      if (result === "SUCCESS") {
        console.log("sender:", sender);
        console.log("response:", response.data);
        setData(response.data);
      }
    } catch (error) {
      console.log(error.response);
      setData({ response: "FAILED", time: new Date() });
    }
  }

  return (
    <div className="Ping">
      <h1 className={data.response}>API Ping: {data.response}</h1>
      <h2>At: {data.time}</h2>
    </div>
  );
}

export default Ping;
