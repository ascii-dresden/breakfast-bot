{ stdenv, pkgs }:

stdenv.mkDerivation {
    name = "breakfastbot";
    buildInputs = [
        (pkgs.python3.withPackages (pythonPackages: with pythonPackages; [
            schedule
            python-telegram-bot
        ] ++ python-telegram-bot.optional-dependencies.job-queue))
    ];
    dontUnpack = true;
    installPhase = "install -Dm755 ${./breakfastbot.py} $out/bin/breakfastbot";
}
