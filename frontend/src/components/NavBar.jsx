import React, { useState } from "react";
import "./css/NavBar.css";
import MainLogo from "./images/logo_white.png";

function NavBar() {
  return (
    <nav className="MainNav">
      <div className="Header">
        <div className="Logo">
          <img src={MainLogo} alt="graphic-portcullis-white" />
        </div>
        <div className="Title">
          <h1>Petition Tracker</h1>

          <h3>UK Government and Parliament (Unofficial)</h3>
        </div>
      </div>
    </nav>
  );
}

export default NavBar;
