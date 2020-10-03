import React, { useState, useEffect, useRef } from "react";
import DatePicker from "react-date-picker";
import moment from "moment";
import _ from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSearch, faHistory, faEye, faCalendarAlt } from "@fortawesome/free-solid-svg-icons";

function TimeNav({ timeChangeHandler, timeConfig = {}, fromNavValue, toNavValue, presetTimeOpts }) {
  const [toggleView, setToggleView] = useState("quick");
  const [presetTimesOpts, setPresetTimeOpts] = useState(presetTimeOpts);
  const [fromValue, onFromChange] = useState(fromNavValue); // range start
  const [toValue, onToChange] = useState(toNavValue); // range end
  const values = { from: fromValue, to: toValue };
  const onChange = { from: onFromChange, to: onToChange };

  useEffect(() => {
    // range start greater than range end?
    if (fromValue > toValue) {
      // set range end to range start
      onToChange(fromValue);
    }
  }, [fromValue]);

  useEffect(() => {
    // range end greater than range start?
    if (toValue < fromValue) {
      // set range start to range end
      onFromChange(toValue);
    }
  }, [toValue]);

  function handleViewToggle(type) {
    setToggleView(type);
  }

  function submitTimeRange() {
    // Allows 1 day ranges to span 24 hours
    const from = moment(fromValue).subtract(23, "hours").toDate();
    const to = moment(toValue).add(59, "minutes").toDate();
    const timeRange = { to: to, from: from };
    console.log("TimeNav range submitted -", timeRange);
    timeChangeHandler(timeRange);
  }

  function submitTimeSince(event) {
    event.preventDefault();
    let options = _.cloneDeep(presetTimesOpts);
    let [unit, value] = [null, null];
    let to = timeConfig.maxDate;
    let from = null;
    if (event.target.type == "radio") {
      unit = event.target.name;
      value = event.target.value;
      const isUnitShowAll = unit.includes("All");

      if (isUnitShowAll) {
        from = timeConfig.minDate;
      } else {
        from = moment(to).subtract(value, unit).toDate();
      }
      options = options.map((opt) => {
        if (opt.selected) {
          opt.selected = false;
        } else if (
          (isUnitShowAll && opt.unit.includes("All")) ||
          (opt.unit === unit && opt.value === parseInt(value))
        ) {
          opt.selected = true;
        }
        return opt;
      });
    } else {
      value = event.target.units.value;
      unit = event.target.amount.value;
      if (value && unit) {
        options = options.map((opt) => {
          opt.selected = false;
          return opt;
        });
      } else {
        return false;
      }

      from = moment(to).subtract(value, unit).toDate();
    }

    const timeRange = { to: to, from: from };
    console.log("TimeNav since submitted -", timeRange);
    onFromChange(from);
    onToChange(to);
    setPresetTimeOpts(options);
    timeChangeHandler(timeRange);
  }

  function renderPicker(type) {
    return (
      <DatePicker
        onChange={onChange[type]}
        value={values[type]}
        minDate={timeConfig.minDate}
        maxDate={timeConfig.maxDate}
        calendarIcon={null}
        clearIcon={null}
        showLeadingZeros={true}
        format={"dd-MM-y"}
      />
    );
  }

  function renderPresets() {
    return (
      <form onChange={submitTimeSince}>
        <div className="container">
          {presetTimesOpts.map((item) => {
            return renderPresetItem(item);
          })}
        </div>
      </form>
    );
  }

  function renderPresetItem(item) {
    const name = `${item.unit.split(" ").join("-")}`;
    const id = `${name}-toggle-${item.value}`;
    return (
      <div className={`${name} preset-item`} key={id}>
        <input
          name={item.unit}
          value={item.value || ""}
          type="radio"
          checked={item.selected}
          readOnly={true}
        />
        <label htmlFor={`${name}-toggle`}>
          <h4>
            <span className="unit">{item.value}</span>
            <span className="nbsp">&nbsp;</span>
            <span className="value">{item.unit}</span>
          </h4>
        </label>
        <div className="pipe">|</div>
      </div>
    );
  }

  function renderQuickSelect() {
    return (
      <div className="quick-selects-wrapper">
        <form id="inputQuickSelectForm" onSubmit={submitTimeSince}>
          <div className="units">
            <select name="units">
              <option value="hours">hours</option>
              <option value="days">days</option>
              <option value="weeks">weeks</option>
            </select>
          </div>
          <div className="amount">
            <input type="text" name="amount" />
          </div>
        </form>

        <div className="presets">{renderPresets()}</div>
      </div>
    );
  }

  function renderToggledView() {
    if (toggleView === "calendar") {
      return (
        <div className="calendar-picker">
          <div className="from">
            <div className="picker">{renderPicker("from")}</div>
          </div>
          <div className="divider">-</div>
          <div className="to">
            <div className="picker">{renderPicker("to")}</div>
          </div>
        </div>
      );
    } else if (toggleView === "quick") {
      return <div className="quick-select">{renderQuickSelect()}</div>;
    }
  }

  return (
    <div className="TimeNav">
      <div className="main">
        <div className="toggle-view buttons">
          <button
            className={`calendar chart-btn ${toggleView === "calendar" ? "selected" : ""}`}
            onClick={() => handleViewToggle("calendar")}
          >
            <div className="icon">
              <FontAwesomeIcon className="fa-fw" icon={faCalendarAlt} />
            </div>
          </button>

          <button
            className={`quick chart-btn  ${toggleView === "quick" ? "selected" : ""}`}
            onClick={() => handleViewToggle("quick")}
          >
            <div className="icon">
              <FontAwesomeIcon className="fa-fw" icon={faHistory} />
            </div>
          </button>
        </div>

        <div className={`view ${toggleView} all`}>{renderToggledView()}</div>

        <div className="submit-time buttons">
          <button
            form="inputQuickSelectForm"
            value="submit"
            className="submit chart-btn"
            onClick={toggleView === "calendar" ? submitTimeRange : null}
          >
            <div className="icon">
              <FontAwesomeIcon className="fa-fw" icon={faEye} />
            </div>
          </button>
        </div>
      </div>
      <div className="mobile">
        <div className="presets"> {renderPresets()} </div>
      </div>
    </div>
  );
}

export default TimeNav;
