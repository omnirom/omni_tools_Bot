/*
 *  Copyright (C) 2013 The OmniROM Project
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

/**
 * Automated patch testing bot. Uses redis to get the patch stack (which
 * itself gets stuff from our gerrit)
 */



 // Imports
 var redis = require("redis"),
    rclient = redis.createClient(),
    sys = require('sys'),
    spawn = require('child_process').spawn;

// Consts
var SOURCE_DIRECTORY = "/home/xplodwild/omni";

// Global variables
var isWorking = false,
    isBuilding = false;

// Redis error handler
rclient.on("error", function (err) {
    console.log("Error " + err);
});

// Helper functions
function puts(error, stdout, stderr) { sys.puts(stdout); sys.puts(stderr); }

// While alive, try to build
function checkPendingBuilds() {
    if (isWorking) return;

    isWorking = true;

    rclient.llen("omnibuild", function(err, reply) {
        console.log(reply + " patches pending");

        // We only take the first one, if any
        if (reply > 0) {
            rclient.lpop("omnibuild", function (err, patch) {
                var json = JSON.parse(patch);
                console.log(json);
                if (json.project.indexOf("android") == 0 && json.project.indexOf("android_device") != 0 &&
                    json.subject.indexOf("1/3") < 0 && json.subject.indexOf("2/3") < 0 && json.subject.indexOf("3/3") < 0 &&
                    json.subject.indexOf("1/4") < 0 && json.subject.indexOf("2/4") < 0 && json.subject.indexOf("3/4") < 0 && json.subject.indexOf("4/4") < 0 &&
                    json.subject.indexOf("1/2") < 0 && json.subject.indexOf("2/2") < 0)
                {
                    testBuild(json.ref);
                } else {
                    console.log("Pruned patch " + json.changeid + " as it is not an android change, or a device change");
                }
            });
        }

        isWorking = false;
    });
}


function testBuild(ref) {
    sys.puts("Testing build with patch " + patchId + " (commit " + ref + ")");
    isBuilding = true;

    var fields = ref.split('/');
    var patchId = fields[3];
    var patchSet = fields[4];

    // Clean environment
    var repoSync = spawn("./build.sh", [patchId, patchSet], {stdio: 'inherit'});

    repoSync.on('close', function (code) {
        isBuilding = false;
    });   
}


setInterval(function() {
    if (!isBuilding) {
        checkPendingBuilds();    
    }
}, 1000);

