import React, { useState, useEffect } from "react";
import moment from "moment";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPencilAlt, faCalendarAlt, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router-dom";

function formatDate(date) {
  return moment(date).format("DD-MM-YYYY");
}

function lazyIntToCommaString(x) {
  return x ? x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "0";
}

function PetitionItem({ item }) {
  return (
    <li className="PetitionItem">
      <div className="banner">
        <div className="id">
          <Link to={`/petition/${item.id}`}>
            <h4># {item.id}</h4>
          </Link>
        </div>
        <div className="external-link">
          <a href={item.url.replace(".json", "")}>
            <span>
              <FontAwesomeIcon className="fa-fw" icon={faExternalLinkAlt} />
            </span>
          </a>
        </div>
      </div>

      <div className="wrapper">
        <div className="content">
          <h4>{item.action}</h4>
          <div className="background">
            <p>{item.background}</p>
          </div>
        </div>
        <div className="meta">
          <div>
            <span className="icon">
              <FontAwesomeIcon className="fa-fw" icon={faCalendarAlt} />
            </span>
            <span>{formatDate(item.pt_created_at)}</span>
          </div>

          <div>
            <span className="icon">
              <FontAwesomeIcon className="fa-fw" icon={faPencilAlt} />
            </span>
            <span>{lazyIntToCommaString(item.signatures)}</span>
          </div>
        </div>
      </div>
    </li>
  );
}

export default PetitionItem;
