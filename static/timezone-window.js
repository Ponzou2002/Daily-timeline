(() => {
    const SCENE_BOUNDARIES = [
        { start: 4, scene: "dawn" },
        { start: 7, scene: "morning" },
        { start: 11, scene: "day" },
        { start: 17, scene: "evening" },
        { start: 19, scene: "night" },
    ];

    const TRASH_ICON = `
        <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            focusable="false"
        >
            <path
                d="M9 3h6l1 2h4v2H4V5h4l1-2Zm-2 6h10l-.7 11H7.7L7 9Zm3 2v7h1.5v-7H10Zm2.5 0v7H14v-7h-1.5Z"
                fill="currentColor"
            />
        </svg>
    `;

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
                laneEnd => entry.start >= laneEnd
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
                && entry.start >= currentGroupEnd
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

        /* Let the existing DOMContentLoaded timeline positioning
           finish first, then calculate shared horizontal lanes. */
        window.setTimeout(updateLayout, 0);

        window.setInterval(updateLayout, 30 * 1000);
        window.addEventListener("resize", updateLayout);
    }

    function createDeleteForm(
        action,
        formClass,
        buttonClass,
        label
    ) {
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

    function initializeTodoDeleteButtons() {
        document
            .querySelectorAll(".todo-item")
            .forEach(item => {
                if (item.querySelector(".todo-delete-form")) {
                    return;
                }

                const completeForm =
                    item.querySelector(".todo-check-form");
                const match = completeForm?.action.match(
                    /\/todo\/(\d+)\/complete\/?$/
                );

                if (!match) {
                    return;
                }

                const todoId = match[1];
                const form = createDeleteForm(
                    `/todo/${todoId}/delete`,
                    "todo-delete-form",
                    "todo-delete-button",
                    "TODOを削除"
                );

                item.appendChild(form);
            });
    }

    async function initializeScheduleDeleteButtons() {
        const planElements = Array.from(
            document.querySelectorAll(".timeline-plan")
        );

        if (!planElements.length) {
            return;
        }

        try {
            const response = await fetch(
                "/schedule/today.json",
                {
                    headers: {
                        Accept: "application/json",
                    },
                    cache: "no-store",
                }
            );

            if (!response.ok) {
                throw new Error(
                    `Schedule metadata request failed: ${response.status}`
                );
            }

            const schedules = await response.json();

            planElements.forEach((plan, index) => {
                if (plan.querySelector(".timeline-plan-delete-form")) {
                    return;
                }

                const scheduleId = schedules[index]?.id;

                if (!scheduleId) {
                    return;
                }

                const form = createDeleteForm(
                    `/schedule/${scheduleId}/delete`,
                    "timeline-plan-delete-form",
                    "timeline-plan-delete-button",
                    "予定を削除"
                );

                plan.appendChild(form);
            });
        } catch (error) {
            console.warn(
                "Could not initialize schedule delete buttons:",
                error
            );
        }
    }

    function initializeDeleteControls() {
        initializeTodoDeleteButtons();
        initializeScheduleDeleteButtons();
    }

    function initialize() {
        initializeDeleteControls();

        const widget = document.querySelector(
            ".current-time-widget"
        );

        if (!widget) {
            return;
        }

        const zoneElement = widget.querySelector("span");
        const timeZone = zoneElement?.textContent.trim();

        if (!timeZone) {
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
            return;
        }

        initializeTimeZoneWindow(widget, formatter);
        initializeTimelineOverlapLayout(formatter);
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