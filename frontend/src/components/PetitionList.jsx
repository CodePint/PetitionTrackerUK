import React, { useState, useEffect, useRef } from "react";
import JSONPretty from "react-json-pretty";
import PetitionItem from "./PetitionItem";
// import "../styles/PetitionList.css";

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
    }
  }

  return (
    <div className="PetitionList">
      {/* <div>{renderJsonList()}</div> */}
      <div>{renderItemList()}</div>
    </div>
  );
}

export default PetitionList;
