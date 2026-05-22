document.addEventListener(
    "DOMContentLoaded",
    async function () {

        try {

            const response =
            await fetch(
                "/api/auth/me",
                {
                    method: "GET",
                    credentials:
                    "include"
                }
            );

            if (!response.ok) {

                window.location.href =
                "/";

                return;
            }

            const user =
            await response.json();

            if (
                user.role !==
                "admin"
            ) {

                document
                .querySelectorAll(
                    ".admin-only"
                )

                .forEach(
                    item =>
                    item.style.display =
                    "none"
                );

                const currentPage =
                window.location.pathname;

                if (

                    currentPage.includes(
                        "logs.html"
                    )

                    ||

                    currentPage.includes(
                        "admin.html"
                    )

                ) {

                    alert(
                        "Admin access only"
                    );

                    window.location.href =
                    "/dashboard.html";

                }

            }

        }

        catch {

            window.location.href =
            "/";

        }

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

                    await fetch(

                        "/api/auth/logout",

                        {
                            method:
                            "POST",

                            credentials:
                            "include"
                        }

                    );

                    window.location.href =
                    "/";

                }

            );

        }

    }
);