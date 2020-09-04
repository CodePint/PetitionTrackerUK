import React, { useState, useEffect, useRef } from "react";
import JSONPretty from "react-json-pretty";
import PetitionItem from "./PetitionItem";
import "./css/PetitionList.css";

function PetitionList({ petitions = [] }) {
  useEffect(() => {}, []);

  function renderJsonList() {
    return (
      <div>
        <JSONPretty id="json-pretty" data={petitions}></JSONPretty>
      </div>
    );
  }

  function renderItemList() {
    if (petitions.length > 0) {
      return (
        <ul>
          {petitions.map((item) => {
            return <PetitionItem item={item}></PetitionItem>;
          })}
        </ul>
      );
    } else {
      return (
        <div>
          <h2>No Petitions Found</h2>
        </div>
      );
    }
  }

  return (
    <div className="PetitionList">
      <h1>Petition List:</h1>

      {/* <div>{renderJsonList()}</div> */}
      <div>{renderItemList()}</div>
    </div>
  );
}

export default PetitionList;
