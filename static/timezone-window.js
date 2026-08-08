(() => {
    const SCENE_BOUNDARIES = [
        { start: 4, scene: "dawn" },
        { start: 7, scene: "morning" },
        { start: 11, scene: "day" },
        { start: 17, scene: "evening" },
        { start: 19, scene: "night" },
    ];

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

    function initializeTimeZoneWindow() {
        const widget =
            document.querySelector(".current-time-widget");

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
                    hourCycle: "h23",
                }
            );
        } catch (error) {
            console.warn(
                "Could not initialize time-zone window:",
                error
            );
            return;
        }

        function updateScene() {
            const hour = Number(
                formatter.format(new Date())
            );

            widget.dataset.timeScene =
                getSceneForHour(hour);
        }

        updateScene();
        window.setInterval(updateScene, 60 * 1000);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeTimeZoneWindow
        );
    } else {
        initializeTimeZoneWindow();
    }
})();
