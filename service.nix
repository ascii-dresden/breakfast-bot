{ config, lib, pkgs, ... }:

let
    gamingbot = pkgs.callPackage ./default.nix {};
    cfg = config.services.gamingbot;

in {
    options.services.gamingbot.enable = lib.mkEnableOption "gamingbot";

    options.services.gamingbot.telegram_api_key = lib.mkOption {
        type = lib.types.str;
        example = "0000:AAAABBBB";
    };

    config = lib.mkIf cfg.enable {
        systemd.services.gamingbot = {
            description = "ASCII gaming bot";
            after = ["network-online.target"];
            wantedBy = ["multi-user.target"];
            wants = ["network-online.target"];
            environment = {
                GAMINGBOT_DATA_DIR = "/var/lib/gamingbot";
            };

            serviceConfig = {
                DynamicUser = "true";
                PrivateDevices = "true";
                ProtectKernelTunables = "true";
                ProtectKernelModules = "true";
                ProtectControlGroups = "true";
                RestrictAddressFamilies = "AF_INET AF_INET6";
                LockPersonality = "true";
                RestrictRealtime = "true";
                SystemCallFilter = "@system-service @network-io @signal";
                SystemCallErrorNumber = "EPERM";
                ExecStart = "${gamingbot}/bin/gamingbot ${cfg.telegram_api_key}";
                StateDirectory = "gamingbot";
                Restart = "always";
                RestartSec = "5";
            };
        };
    };
}
