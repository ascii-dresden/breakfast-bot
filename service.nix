{ config, lib, pkgs, ... }:

let
    breakfastbot = pkgs.callPackage ./default.nix {};
    cfg = config.services.breakfastbot;

in {
    options.services.breakfastbot.enable = lib.mkEnableOption "breakfastbot";

    options.services.breakfastbot.telegram_api_key = lib.mkOption {
        type = lib.types.str;
        example = "0000:AAAABBBB";
    };

    config = lib.mkIf cfg.enable {
        systemd.services.breakfastbot = {
            description = "ASCII breakfast bot";
            after = ["network-online.target"];
            wantedBy = ["network-online.target"];

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
                ExecStart = "${breakfastbot}/bin/breakfastbot ${cfg.telegram_api_key}";
                Restart = "always";
                RestartSec = "5";
            };
        };
    };
}
