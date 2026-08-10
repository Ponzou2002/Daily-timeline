(() => {
    const SCENE_BOUNDARIES = [
        { start: 4, scene: "dawn" },
        { start: 7, scene: "morning" },
        { start: 11, scene: "day" },
        { start: 17, scene: "evening" },
        { start: 19, scene: "night" },
    ];

    const TRASH_ICON = `
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
                d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-2 6h10l-.7 11H7.7L7 9Zm3 2v7h1.5v-7H10Zm2.5 0v7H14v-7h-1.5Z"
                fill="currentColor"
            />
        </svg>
    `;

    const EDIT_ICON = `
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
                d="M4 20h4l11-11-4-4L4 16v4Zm9.5-13.5 4 4M14.5 5.5l2-2a1.4 1.4 0 0 1 2 0l2 2a1.4 1.4 0 0 1 0 2l-2 2"
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
            />
        </svg>
    `;

    const TIMELINE_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
    const TIMELINE_OVERLAP_EPSILON = 1e-7;

    function getSceneForHour(hour) {
        if (hour < 4 || hour >= 19) {
            return "night";
        }

        let scene = "night";

        for (const boundary of SCENE_BOUNDARIES) {
            if (hour >= boundary.start) {
                scene = boundary.scene;
            }
        }

        return scene;
    }

    function getTimeParts(formatter) {
        const values = {};

        formatter
            .formatToParts(new Date())
            .forEach(part => {
                if (
                    part.type === "hour"
                    || part.type === "minute"
                    || part.type === "second"
                ) {
                    values[part.type] = Number(part.value);
                }
            });

        return values;
    }

    function getConfiguredDateKey(timeZone) {
        const formatter = new Intl.DateTimeFormat(
            "en-CA",
            {
                timeZone,
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
            }
        );
        const values = {};

        formatter
            .formatToParts(new Date())
            .forEach(part => {
                if (
                    part.type === "year"
                    || part.type === "month"
                    || part.type === "day"
                ) {
                    values[part.type] = part.value;
                }
            });

        return `${values.year}-${values.month}-${values.day}`;
    }

    function getRequestedTimelineDate() {
        const value = new URLSearchParams(
            window.location.search
        ).get("date");

        if (!value || !TIMELINE_DATE_PATTERN.test(value)) {
            return null;
        }

        return value;
    }

    function shiftDate(dateKey, amount) {
        const date = new Date(`${dateKey}T12:00:00Z`);
        date.setUTCDate(date.getUTCDate() + amount);
        return date.toISOString().slice(0, 10);
    }

    function withTimelineDate(path) {
        const dateKey = getRequestedTimelineDate();

        if (!dateKey) {
            return path;
        }

        const separator = path.includes("?") ? "&" : "?";
        return `${path}${separator}date=${encodeURIComponent(dateKey)}`;
    }

    function ensureTimelineDateStylesheet() {
        if (document.getElementById("timeline-date-stylesheet")) {
            return;
        }

        const link = document.createElement("link");
        link.id = "timeline-date-stylesheet";
        link.rel = "stylesheet";
        link.href = "/static/timeline-date.css";
        document.head.appendChild(link);
    }

    function initializeTimelineDateNavigation(timeZone) {
        ensureTimelineDateStylesheet();

        const today = getConfiguredDateKey(timeZone);
        const requestedDate = getRequestedTimelineDate();
        const selectedDate = requestedDate || today;
        const isToday = selectedDate === today;

        const heading = document.querySelector(".timeline-heading");
        const headingCopy = document.querySelector(
            ".timeline-heading-copy"
        );
        const addButton = document.getElementById(
            "add-schedule-open"
        );

        if (headingCopy) {
            const title = headingCopy.querySelector("h2");
            const subtitle = headingCopy.querySelector("span");

            if (title) {
                title.textContent = isToday
                    ? "TODAY TIMELINE"
                    : "DAY TIMELINE";
            }

            if (subtitle) {
                subtitle.textContent = isToday
                    ? "今日の記録"
                    : selectedDate;
            }
        }

        if (
            heading
            && addButton
            && !document.querySelector(".timeline-date-nav")
        ) {
            const nav = document.createElement("nav");
            nav.className = "timeline-date-nav";
            nav.setAttribute("aria-label", "Timeline date navigation");

            const previous = document.createElement("a");
            previous.className = "timeline-date-step";
            previous.href = `/?date=${shiftDate(selectedDate, -1)}`;
            previous.textContent = "‹";
            previous.setAttribute("aria-label", "前の日");
            previous.title = "前の日";

            const label = document.createElement("span");
            label.className = "timeline-date-label";
            label.textContent = selectedDate;

            const next = document.createElement("a");
            next.className = "timeline-date-step";
            next.href = `/?date=${shiftDate(selectedDate, 1)}`;
            next.textContent = "›";
            next.setAttribute("aria-label", "次の日");
            next.title = "次の日";

            const todayLink = document.createElement("a");
            todayLink.className =
                `timeline-date-today${isToday ? " is-active" : ""}`;
            todayLink.href = "/";
            todayLink.textContent = "TODAY";

            nav.append(
                previous,
                label,
                next,
                todayLink
            );
            heading.insertBefore(nav, addButton);
        }

        const scheduleForm = document.getElementById(
            "schedule-form"
        );
        const scheduleDate = document.getElementById(
            "schedule-date"
        );

        if (scheduleForm) {
            scheduleForm.action = withTimelineDate(
                "/schedule/add"
            );
        }

        if (scheduleDate) {
            scheduleDate.value = selectedDate;
        }

        if (!isToday) {
            const nowLine = document.getElementById("timeline-now");
            nowLine?.remove();

            const currentActivity = document.getElementById(
                "timeline-current-activity"
            );

            if (currentActivity) {
                currentActivity.removeAttribute("id");
                currentActivity.classList.remove("is-current");

                if (selectedDate < today) {
                    const timeLabel = currentActivity.querySelector(
                        ".timeline-activity-time"
                    );

                    if (timeLabel) {
                        timeLabel.textContent = timeLabel.textContent
                            .replace(/\s*–\s*NOW\s*$/, " – 00:00");
                    }
                }
            }
        }
    }

    function initializeTimeZoneWindow(widget, formatter) {
        function updateScene() {
            const time = getTimeParts(formatter);

            widget.dataset.timeScene =
                getSceneForHour(time.hour);
        }

        updateScene();
        window.setInterval(updateScene, 60 * 1000);
    }

    function readPercentVariable(element, variableName) {
        const value = element.style
            .getPropertyValue(variableName)
            .trim();

        const number = Number.parseFloat(value);

        return Number.isFinite(number) ? number : 0;
    }

    function moveActivitiesIntoSharedLayer(layer) {
        const timelineBody = layer.parentElement;

        if (!timelineBody) {
            return;
        }

        const activities = Array.from(
            timelineBody.children
        ).filter(element =>
            element.classList.contains("timeline-activity")
        );

        activities.forEach(activity => {
            layer.appendChild(activity);
        });
    }

    function getTimelineEntryRange(
        element,
        currentMinute
    ) {
        const isActivity =
            element.classList.contains("timeline-activity");

        let startPercent;
        let heightPercent;

        if (isActivity) {
            startPercent = Number(
                element.dataset.startPercent
            );
            heightPercent = Number(
                element.dataset.heightPercent
            );

            if (
                element.id === "timeline-current-activity"
                && Number.isFinite(currentMinute)
            ) {
                const startMinute = Number(
                    element.dataset.startMinute
                );

                heightPercent = (
                    Math.max(0, currentMinute - startMinute)
                    / 1440
                    * 100
                );
            }
        } else {
            startPercent = readPercentVariable(
                element,
                "--schedule-top"
            );
            heightPercent = readPercentVariable(
                element,
                "--schedule-height"
            );
        }

        if (
            !Number.isFinite(startPercent)
            || !Number.isFinite(heightPercent)
        ) {
            return null;
        }

        return {
            element,
            start: startPercent,
            end: startPercent + Math.max(0, heightPercent),
            priority: isActivity ? 0 : 1,
        };
    }

    function assignGroupLanes(group) {
        const laneEnds = [];

        const orderedEntries = [...group].sort(
            (left, right) =>
                left.priority - right.priority
                || left.start - right.start
                || left.end - right.end
        );

        orderedEntries.forEach(entry => {
            let laneIndex = laneEnds.findIndex(
                laneEnd => (
                    entry.start + TIMELINE_OVERLAP_EPSILON
                    >= laneEnd
                )
            );

            if (laneIndex === -1) {
                laneIndex = laneEnds.length;
                laneEnds.push(entry.end);
            } else {
                laneEnds[laneIndex] = entry.end;
            }

            entry.laneIndex = laneIndex;
        });

        const laneCount = Math.max(1, laneEnds.length);

        group.forEach(entry => {
            const left =
                entry.laneIndex / laneCount * 100;
            const width = 100 / laneCount;

            entry.element.style.setProperty(
                "--schedule-left",
                `${left}%`
            );
            entry.element.style.setProperty(
                "--schedule-width",
                `${width}%`
            );

            entry.element.dataset.lane =
                String(entry.laneIndex);
            entry.element.dataset.laneCount =
                String(laneCount);
        });
    }

    function layoutTimelineEntries(formatter) {
        const layer = document.querySelector(
            ".timeline-plan-layer"
        );

        if (!layer) {
            return;
        }

        const time = getTimeParts(formatter);
        const currentMinute =
            time.hour * 60
            + time.minute
            + time.second / 60;

        const entries = Array.from(
            layer.querySelectorAll(
                ".timeline-activity, .timeline-plan"
            )
        )
            .map(element =>
                getTimelineEntryRange(
                    element,
                    currentMinute
                )
            )
            .filter(Boolean)
            .sort(
                (left, right) =>
                    left.start - right.start
                    || left.end - right.end
            );

        if (!entries.length) {
            return;
        }

        const groups = [];
        let currentGroup = [];
        let currentGroupEnd = null;

        entries.forEach(entry => {
            if (
                currentGroup.length
                && entry.start + TIMELINE_OVERLAP_EPSILON
                    >= currentGroupEnd
            ) {
                groups.push(currentGroup);
                currentGroup = [];
                currentGroupEnd = null;
            }

            currentGroup.push(entry);

            currentGroupEnd = currentGroupEnd === null
                ? entry.end
                : Math.max(currentGroupEnd, entry.end);
        });

        if (currentGroup.length) {
            groups.push(currentGroup);
        }

        groups.forEach(assignGroupLanes);
    }

    function initializeTimelineOverlapLayout(formatter) {
        const layer = document.querySelector(
            ".timeline-plan-layer"
        );

        if (!layer) {
            return;
        }

        moveActivitiesIntoSharedLayer(layer);

        const updateLayout = () => {
            layoutTimelineEntries(formatter);
        };

        window.setTimeout(updateLayout, 0);
        window.setInterval(updateLayout, 30 * 1000);
        window.addEventListener("resize", updateLayout);
    }

    function createDeleteForm(action, formClass, buttonClass, label) {
        const form = document.createElement("form");
        form.method = "post";
        form.action = action;
        form.className = formClass;

        const button = document.createElement("button");
        button.type = "submit";
        button.className = buttonClass;
        button.setAttribute("aria-label", label);
        button.title = label;
        button.innerHTML = TRASH_ICON;

        form.appendChild(button);
        return form;
    }

    function createEditDialog() {
        let dialog = document.getElementById(
            "timeline-edit-dialog"
        );

        if (dialog) {
            return dialog;
        }

        dialog = document.createElement("dialog");
        dialog.id = "timeline-edit-dialog";
        dialog.className =
            "schedule-dialog timeline-edit-dialog";

        dialog.innerHTML = `
            <div class="schedule-dialog-shell">
                <header class="schedule-dialog-header">
                    <div class="schedule-dialog-title">
                        <h2 id="timeline-edit-title">EDIT</h2>
                        <span id="timeline-edit-subtitle"></span>
                    </div>

                    <button
                        id="timeline-edit-close"
                        class="schedule-dialog-close"
                        type="button"
                        aria-label="編集画面を閉じる"
                    >×</button>
                </header>

                <form
                    id="timeline-edit-form"
                    method="post"
                    class="schedule-form timeline-edit-form"
                >
                    <label class="schedule-field">
                        <span>NAME</span>
                        <input
                            id="timeline-edit-name"
                            type="text"
                            name="name"
                            autocomplete="off"
                            required
                        >
                    </label>

                    <div class="timeline-edit-range">
                        <fieldset class="timeline-edit-period">
                            <legend>START</legend>

                            <span class="schedule-date-input-shell">
                                <input
                                    id="timeline-edit-start-date"
                                    type="date"
                                    name="start_date"
                                    required
                                >
                            </span>

                            <div class="schedule-clock-selects">
                                <select
                                    id="timeline-edit-start-hour"
                                    name="start_hour"
                                    aria-label="開始時"
                                    required
                                ></select>

                                <span class="schedule-clock-separator">:</span>

                                <select
                                    id="timeline-edit-start-minute"
                                    name="start_minute"
                                    aria-label="開始分"
                                    required
                                ></select>
                            </div>
                        </fieldset>

                        <fieldset
                            id="timeline-edit-end-period"
                            class="timeline-edit-period"
                        >
                            <legend>END</legend>

                            <span class="schedule-date-input-shell">
                                <input
                                    id="timeline-edit-end-date"
                                    type="date"
                                    name="end_date"
                                    required
                                >
                            </span>

                            <div class="schedule-clock-selects">
                                <select
                                    id="timeline-edit-end-hour"
                                    name="end_hour"
                                    aria-label="終了時"
                                    required
                                ></select>

                                <span class="schedule-clock-separator">:</span>

                                <select
                                    id="timeline-edit-end-minute"
                                    name="end_minute"
                                    aria-label="終了分"
                                    required
                                ></select>
                            </div>
                        </fieldset>
                    </div>

                    <div
                        id="timeline-edit-current-note"
                        class="timeline-edit-current-note"
                        hidden
                    >
                        END <strong>NOW</strong>
                        <span>進行中のActivityなので終了時刻は変更しません。</span>
                    </div>

                    <div class="schedule-dialog-actions">
                        <button
                            id="timeline-edit-cancel"
                            class="schedule-dialog-cancel"
                            type="button"
                        >CANCEL</button>

                        <button
                            class="schedule-dialog-submit"
                            type="submit"
                        >SAVE</button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(dialog);
        return dialog;
    }

    function fillHourSelect(select, value) {
        select.innerHTML = "";

        for (let hour = 0; hour < 24; hour += 1) {
            const option = document.createElement("option");
            option.value = String(hour);
            option.textContent =
                String(hour).padStart(2, "0");
            select.appendChild(option);
        }

        select.value = String(value);
    }

    function fillMinuteSelect(select, value) {
        const minutes = [0, 10, 20, 30, 40, 50];
        const numericValue = Number(value);

        if (!minutes.includes(numericValue)) {
            minutes.push(numericValue);
            minutes.sort((left, right) => left - right);
        }

        select.innerHTML = "";

        minutes.forEach(minute => {
            const option = document.createElement("option");
            option.value = String(minute);
            option.textContent =
                String(minute).padStart(2, "0");
            select.appendChild(option);
        });

        select.value = String(numericValue);
    }

    function initializeEditDialog() {
        const dialog = createEditDialog();
        const form = document.getElementById("timeline-edit-form");
        const title = document.getElementById("timeline-edit-title");
        const subtitle = document.getElementById("timeline-edit-subtitle");
        const closeButton = document.getElementById("timeline-edit-close");
        const cancelButton = document.getElementById("timeline-edit-cancel");
        const nameInput = document.getElementById("timeline-edit-name");
        const startDate = document.getElementById("timeline-edit-start-date");
        const startHour = document.getElementById("timeline-edit-start-hour");
        const startMinute = document.getElementById("timeline-edit-start-minute");
        const endPeriod = document.getElementById("timeline-edit-end-period");
        const endDate = document.getElementById("timeline-edit-end-date");
        const endHour = document.getElementById("timeline-edit-end-hour");
        const endMinute = document.getElementById("timeline-edit-end-minute");
        const currentNote = document.getElementById("timeline-edit-current-note");

        function closeDialog() {
            dialog.close();
        }

        closeButton.addEventListener("click", closeDialog);
        cancelButton.addEventListener("click", closeDialog);

        dialog.addEventListener("click", event => {
            if (event.target === dialog) {
                closeDialog();
            }
        });

        function getDateTimeKey(dateInput, hourSelect, minuteSelect) {
            if (
                !dateInput.value
                || hourSelect.value === ""
                || minuteSelect.value === ""
            ) {
                return null;
            }

            return [
                dateInput.value,
                "T",
                String(hourSelect.value).padStart(2, "0"),
                ":",
                String(minuteSelect.value).padStart(2, "0")
            ].join("");
        }

        function validateTimes() {
            endMinute.setCustomValidity("");

            if (endPeriod.hidden) {
                return;
            }

            const start = getDateTimeKey(
                startDate,
                startHour,
                startMinute
            );
            const end = getDateTimeKey(
                endDate,
                endHour,
                endMinute
            );

            if (start && end && end <= start) {
                endMinute.setCustomValidity(
                    "終了時刻は開始時刻より後にしてください。"
                );
            }
        }

        [
            startDate,
            startHour,
            startMinute,
            endDate,
            endHour,
            endMinute
        ].forEach(control => {
            control.addEventListener("change", validateTimes);
        });

        form.addEventListener("submit", event => {
            validateTimes();

            if (!form.reportValidity()) {
                event.preventDefault();
            }
        });

        function openEntry(entry, type) {
            const isCurrent =
                type === "activity" && entry.is_current;

            form.action = type === "activity"
                ? withTimelineDate(`/activity/${entry.id}/edit`)
                : withTimelineDate(`/schedule/${entry.id}/edit`);

            title.textContent = type === "activity"
                ? "EDIT ACTIVITY"
                : "EDIT SCHEDULE";

            subtitle.textContent = type === "activity"
                ? "実績の名前・日時を変更"
                : "手動予定の名前・日時を変更";

            nameInput.value = entry.name;
            startDate.value = entry.start_date;
            fillHourSelect(startHour, entry.start_hour);
            fillMinuteSelect(startMinute, entry.start_minute);

            endPeriod.hidden = isCurrent;
            currentNote.hidden = !isCurrent;

            [endDate, endHour, endMinute].forEach(control => {
                control.disabled = isCurrent;
            });

            if (!isCurrent) {
                endDate.value = entry.end_date;
                fillHourSelect(endHour, entry.end_hour);
                fillMinuteSelect(endMinute, entry.end_minute);
            }

            endMinute.setCustomValidity("");
            dialog.showModal();

            window.setTimeout(() => {
                nameInput.focus();
                nameInput.select();
            }, 0);
        }

        return openEntry;
    }

    function addEntryEditControl(element, entry, type, openEntry) {
        if (!element || !entry) {
            return;
        }

        element.dataset.entryType = type;
        element.dataset.entryId = String(entry.id);
        element.classList.add("is-editable-entry");

        if (!element.querySelector(".timeline-entry-edit-button")) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "timeline-entry-edit-button";
            button.setAttribute(
                "aria-label",
                type === "activity"
                    ? "Activityを編集"
                    : "予定を編集"
            );
            button.title = "編集";
            button.innerHTML = EDIT_ICON;

            button.addEventListener("click", event => {
                event.stopPropagation();
                openEntry(entry, type);
            });

            element.appendChild(button);
        }

        if (!element.dataset.editClickAttached) {
            element.addEventListener("click", event => {
                if (event.target.closest("button, form, input, select")) {
                    return;
                }

                openEntry(entry, type);
            });

            element.dataset.editClickAttached = "true";
        }
    }

    function ensureScheduleDeleteControl(element, entry) {
        if (
            !element
            || !entry
            || element.querySelector(".timeline-plan-delete-form")
        ) {
            return;
        }

        const form = createDeleteForm(
            withTimelineDate(`/schedule/${entry.id}/delete`),
            "timeline-plan-delete-form",
            "timeline-plan-delete-button",
            "予定を削除"
        );

        element.appendChild(form);
    }

    function ensureTodoDeleteControls(todoEntries) {
        const todoItems = Array.from(
            document.querySelectorAll(".todo-item")
        );

        todoItems.forEach((element, index) => {
            const entry = todoEntries[index];

            if (
                !entry
                || element.querySelector(".todo-delete-form")
            ) {
                return;
            }

            const form = createDeleteForm(
                `/todo/${entry.id}/delete`,
                "todo-delete-form",
                "todo-delete-button",
                "TODOを削除"
            );

            element.appendChild(form);
        });
    }

    async function initializeTimelineEntryEditing() {
        const openEntry = initializeEditDialog();

        let response;

        try {
            response = await fetch(
                withTimelineDate("/timeline/edit-data.json"),
                {
                    headers: {
                        Accept: "application/json",
                    },
                    cache: "no-store",
                }
            );
        } catch (error) {
            console.warn(
                "Could not load timeline edit data:",
                error
            );
            return;
        }

        if (!response.ok) {
            console.warn(
                "Could not load timeline edit data:",
                response.status
            );
            return;
        }

        const data = await response.json();

        const activityElements = Array.from(
            document.querySelectorAll(".timeline-activity")
        );
        const scheduleElements = Array.from(
            document.querySelectorAll(".timeline-plan")
        );

        activityElements.forEach((element, index) => {
            addEntryEditControl(
                element,
                data.activities[index],
                "activity",
                openEntry
            );
        });

        scheduleElements.forEach((element, index) => {
            const entry = data.schedules[index];

            addEntryEditControl(
                element,
                entry,
                "schedule",
                openEntry
            );
            ensureScheduleDeleteControl(element, entry);
        });

        ensureTodoDeleteControls(data.todos || []);
    }

    function initialize() {
        const widget = document.querySelector(
            ".current-time-widget"
        );

        if (!widget) {
            initializeTimelineEntryEditing();
            return;
        }

        const zoneElement = widget.querySelector("span");
        const timeZone = zoneElement?.textContent.trim();

        if (!timeZone) {
            initializeTimelineEntryEditing();
            return;
        }

        let formatter;

        try {
            formatter = new Intl.DateTimeFormat(
                "en-GB",
                {
                    timeZone,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hourCycle: "h23",
                }
            );
        } catch (error) {
            console.warn(
                "Could not initialize time-zone UI:",
                error
            );
            initializeTimelineEntryEditing();
            return;
        }

        initializeTimelineDateNavigation(timeZone);
        initializeTimeZoneWindow(widget, formatter);
        initializeTimelineOverlapLayout(formatter);
        initializeTimelineEntryEditing();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initialize
        );
    } else {
        initialize();
    }
})();