/*
* Copyright 2017 the Isard-vdi project authors:
*      Josep Maria Viñolas Auquer
*      Alberto Larraz Dalmases
* License: AGPLv3
*/

	function detectXpiPlugin(){
		var pluginsFound = false;
		if (navigator.plugins && navigator.plugins.length > 0) {
			var daPlugins = [ "Spice" ];
			var pluginsAmount = navigator.plugins.length;
			for (counter = 0; counter < pluginsAmount; counter++) {
				var numFound = 0;
				for (namesCounter = 0; namesCounter < daPlugins.length; namesCounter++) {
					if ((navigator.plugins[counter].name.indexOf(daPlugins[namesCounter]) > 0)
						|| (navigator.plugins[counter].description.indexOf(daPlugins[namesCounter]) >= 0)) {
						numFound++;
					}
				}
				if (numFound == daPlugins.length) {
				pluginsFound = true;
				break;
				}
			}

		}
		return pluginsFound;
	}


	function openTCP(spice_host,spice_port,spice_passwd)
	{
		var embed = document.embeds[0];
		embed.hostIP = spice_host;
		embed.port = spice_port;
		embed.Password = spice_passwd;
		embed.fullScreen = true;
		embed.fAudio = true;
		embed.UsbListenPort = 1;
		embed.UsbAutoShare = 1;
		embed.connect();
	}

	function openTLS(spice_host,spice_port,spice_tls,spice_passwd,ca)
	{		
		var embed = document.embeds[0];
		embed.hostIP = spice_host;
		//~ embed.port = spice_port;
		embed.SecurePort = spice_tls;
		embed.Password = spice_passwd;
		embed.CipherSuite = "";
		embed.SSLChannels = "";
		embed.HostSubject = "";
		embed.fullScreen = true;
		embed.AdminConsole = "";
		embed.Title = "";
		embed.dynamicMenu = "";
		embed.NumberOfMonitors = "";
		embed.GuestHostName = "";
		embed.HotKey = "";
		embed.NoTaskMgrExecution = "";
		embed.SendCtrlAltDelete = "";
		embed.UsbListenPort = "";
		embed.UsbAutoShare = true;
		embed.Smartcard = "";
		embed.ColorDepth = "";
		embed.DisableEffects = "";
		embed.TrustStore = ca;
		embed.Proxy = "";
		embed.connect();
	}
  
