import React, { useState, useEffect, useRef } from "react";
import JSONPretty from "react-json-pretty";
import PetitionItem from "./PetitionItem";

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
      <div>{renderItemList()}</div>
    </div>
  );
}

export default PetitionList;
