{ stdenv, pkgs }:

stdenv.mkDerivation {
    name = "gamingbot";
    buildInputs = [
        (pkgs.python3.withPackages (pythonPackages: with pythonPackages; [
            schedule
            python-telegram-bot
        ] ++ python-telegram-bot.optional-dependencies.job-queue))
    ];
    dontUnpack = true;
    installPhase = "install -Dm755 ${./gamingbot.py} $out/bin/gamingbot";
}
