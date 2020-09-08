import React, { useState, useEffect, useRef } from "react";
import ReactDOM from "react-dom";
import { useAnimate } from "react-simple-animate";
import { Animate, AnimateKeyframes, AnimateGroup } from "react-simple-animate";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import PortcullisWhite from "../images/portcullis_white.png";
import CrownWhite from "../images/crown_white.png";

const icon_choices = {
  crown: CrownWhite,
  portcullis: PortcullisWhite,
};

function ProgressBar({
  play,
  label = { text: "", icon: "" },
  start = 0,
  progress = 0,
  threshold = 100,
}) {
  const thresholdReached = progress >= threshold;
  const percentageComplete = getCompletionPercentage();

  function lazyIntToCommaString(x) {
    return x ? x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "";
  }

  function getCompletionPercentage() {
    return thresholdReached ? 100 : Math.round((progress / threshold) * 100);
  }

  function renderLabel() {
    return (
      <div className="label__container">
        <div className={`icon ${label.icon}`}>
          <img src={icon_choices[label.icon]} />
        </div>
        <h3>{label.text} </h3>
      </div>
    );
  }

  function renderThreshold() {
    return (
      <div>
        <span>{lazyIntToCommaString(threshold)}</span>
      </div>
    );
  }

  return (
    <div className="ProgressBar">
      <div className="label">{renderLabel()}</div>
      <div className="container">
        <Animate
          play={play}
          duration={2}
          delay={0}
          start={{ width: "100%", maxWidth: `${start}%` }}
          end={{ width: "100%", maxWidth: `${percentageComplete}%` }}
          complete={{ width: "100%", maxWidth: `${percentageComplete}%` }}
          easeType={"ease-out"}
        >
          <Bar></Bar>
        </Animate>
      </div>
      <div className="threshold">{renderThreshold()}</div>
    </div>
  );
}

function Bar() {
  return <div className="Bar"></div>;
}

export default ProgressBar;
