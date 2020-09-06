import React, { useState, useEffect } from "react";
// import "../styles/PetitionItem.css";

function PetitionItem({ item }) {
  return (
    <li className="PetitionItem">
      <br></br>
      <div>
        <div>
          <h3>ID: {item.id}</h3>
          <h4>Action: {item.action}</h4>
        </div>
        <div>Created at: {item.pt_created_at}</div>
        <div>Signatures: {item.signatures}</div>
      </div>
      <br></br>
    </li>
  );
}

export default PetitionItem;
