window.addEventListener(
    "load",
    async function () {

        document.body.style.visibility =
        "visible";

        try {

            const response =
            await fetch(

                "/api/auth/me",

                {
                    method:
                    "GET",

                    credentials:
                    "include"
                }

            );

            if (
                !response.ok
            ) {

                window.location.href =
                "/";

                return;
            }

            const user =
            await response.json();

            // HIDE ADMIN MENUS

            if (

                user.role !==
                "admin"

            ) {

                document
                .querySelectorAll(
                    ".admin-only"
                )

                .forEach(

                    item => {

                        item.style.display =
                        "none";

                    }

                );

                // BLOCK DIRECT ACCESS

                const page =

                window.location.pathname;

                if (

                    page.includes(
                        "logs.html"
                    )

                    ||

                    page.includes(
                        "admin.html"
                    )

                ) {

                    alert(
                        "Admin access only"
                    );

                    window.location.href =
                    "/dashboard.html";

                    return;

                }

            }

            // ACTIVE SIDEBAR

            document
            .querySelectorAll(
                ".sidebar a"
            )

            .forEach(

                link => {

                    link.classList.remove(
                        "active"
                    );

                    if (

                        window.location.pathname
                        .includes(

                            link.getAttribute(
                                "href"
                            )

                        )

                    ) {

                        link.classList.add(
                            "active"
                        );

                    }

                }

            );

        }

        catch (

            error

        ) {

            console.error(
                error
            );

            window.location.href =
            "/";

        }

        // LOGOUT

        const logoutBtn =

        document.getElementById(
            "logoutBtn"
        );

        if (

            logoutBtn

        ) {

            logoutBtn
            .addEventListener(

                "click",

                async () => {

                    try {

                        await fetch(

                            "/api/auth/logout",

                            {
                                method:
                                "POST",

                                credentials:
                                "include"
                            }

                        );

                    }

                    catch {}

                    window.location.href =
                    "/";

                }

            );

        }

    }
);