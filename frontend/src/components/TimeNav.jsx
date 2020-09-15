import React, { useState, useEffect, useRef } from "react";
import DateTimePicker from "react-datetime-picker";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSearch, faHistory, faEye } from "@fortawesome/free-solid-svg-icons";

function TimeNav({
  timeChangeHandler,
  timeConfig = {},
  fromNavValue = new Date(),
  toNavValue = new Date(),
}) {
  const [componentMinDate, setComponentMinDate] = useState(null);
  const [componentMaxDate, setComponentMaxDate] = useState(null);

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

  function submit() {
    const NewTimeRange = { to: toValue, from: fromValue };
    timeChangeHandler(NewTimeRange);
  }

  function renderPicker(type) {
    return (
      <DateTimePicker
        onChange={onChange[type]}
        value={values[type]}
        minDate={timeConfig.minDate}
        maxDate={timeConfig.maxDate}
        calendarIcon={null}
        clearIcon={null}
      />
    );
  }

  return (
    <div className="TimeNav">
      <div className="from">{renderPicker("from")}</div>
      <div className="dash">-</div>
      <div className="to">{renderPicker("to")}</div>
      <div className="buttons">
        <div className="submit btn">
          <button onClick={submit}>
            <div className="icon">
              <FontAwesomeIcon className="fa-fw" icon={faEye} />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}

export default TimeNav;

// function addTimeToDate(date, value, unit) {
//   return moment(date).add(value, unit);
// }
