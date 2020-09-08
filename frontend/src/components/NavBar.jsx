import React, { useState } from "react";
import { Link } from "react-router-dom";
import MainLogo from "../images/portcullis_white.png";

function NavBar() {
  return (
    <nav className="MainNav">
      <div className="Header">
        <div className="Logo">
          <Link to={"/"}>
            {" "}
            <img src={MainLogo} alt="graphic-portcullis-white" />
          </Link>
        </div>

        <div className="Title">
          <Link to={"/"}>
            <h1>Petition Tracker</h1>

            <h3>UK Government and Parliament (Unofficial)</h3>
          </Link>
        </div>
      </div>
    </nav>
  );
}

export default NavBar;
