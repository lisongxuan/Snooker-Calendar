const en = {
    header: {
        title:"Snooker Calendar",
        about:"About",
        author:"Developer",
        github:"GitHub Repository",
        contactmail:"Feedback Email(Click to Copy)",
        updatelog:"Update Log",
        temporary:"No",
        copysuccess:"Copy Success",
        copyfail:"Copy Failed",
        selectlanguagesuccess:"Language switched, please refresh the page if there is any problem",
        latestEventInfoDate:"Latest Event Info Updated",
        latestPlayerInfoDate:"Latest Player Info Updated",
        noData:"No Data",
    },
    app:{
        en:"English",
        jp:"Japanese",
        cn:"Chinese",
        de:"German",
        fr:"French",
        kr:"Korean",
        allLanguages:"All Languages",
        position:"Position",
        name:"Name",
        sumValue:"Sum Value",
        rankingTitles:"Ranking Titles",
        downloadICS:"Download ICS",
        googleCalendar:"Google Calendar",
        lastUpdated:"Last Updated",
        latestPlayerInfoDate:"Latest Player Info Date",
        latestEventInfoDate:"Latest Event Info Date",
        noData:"Data not loaded, please refresh the page",
        copyIcsLink:"Copy ICS Link",
        download:"Download",
        subscribe:"Subscribe",
        copy:"Copy",
        datasource:"All data comes from Snooker.org"
    },
    updateLog:{
        title:"Update Log",
        pageTitle:"Update Log - Snooker Calendar",
        content:[
            {
                version:"1.0.0",
                date:"2025-11-28",
                detail:[
                    "1. Basic functions implemented",
                ]
            },
            {
                version:"1.1.0",
                date:"2025-11-30",
                detail:[
                    "1. Added last updated time display and timezone adaptation",
                    "2. Fixed some known issues",
                ]
            },
            {
                version:"1.2.0",
                date:"2026-09-04",
                detail:[
                    "1. Faster page loading and data refresh thanks to improved caching",
                    "2. Data updates are more reliable and less likely to get stuck",
                    "3. Fixed an issue where the page showed empty data after a period of inactivity; it now loads normally on first visit",
                    "4. Improved the message shown when data fails to load",
                    "5. Calendar (ICS) generation is more stable and less likely to fail or hang",
                ]
            }
        ]
    }
}
export default en;