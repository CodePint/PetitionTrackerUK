import React, { useState } from "react";
import PetitionListController from "./PetitionListController";
import "./css/Home.css";

function Home() {
  return (
    <div className="Home">
      <PetitionListController></PetitionListController>
    </div>
  );
}

export default Home;
