from datetime import datetime
from logger import log

import subprocess
import webbrowser
import logging
import os.path
import psutil
import shutil
import time
import re

bifExp = r"\"BaseInstallFolder_[\d+]\"[\s]+\"(.*)\""

gameLibrary = ""
steamPath = ""
gamePath = ""
gameDir = "\\steamapps\\common\\team fortress 2\\tf\\"
gameFiles = [
    "\\steamapps\\common\\team fortress 2\\hl2.exe",
    "\\steamapps\\common\\team fortress 2\\tf\\",
    "\\steamapps\\common\\team fortress 2\\tf\\bin\\",
    "\\steamapps\\common\\team fortress 2\\tf\\bin\\client.dll",
]


def getSteamProcess():
  for p in psutil.process_iter(attrs=["name"]):
    if p.info["name"].lower() == "steam.exe":
      return p

  return None


def getTF2Process():
  for p in psutil.process_iter(attrs=["name"]):
    if p.info["name"].lower() == "hl2.exe":
      return p

  return None


# finds steam's path
def findPath():
  global steamPath
  global gamePath

  log.debug("finding steam's path...")
  steamExePath = getSteamProcess().exe()

  if steamExePath == "":
    return ""

  steamPath = os.path.split(steamExePath)[0]
  log.debug("found steam's path: " + steamPath)
  return steamPath


# gets the list of steam libraries
def findLibraries():
  log.debug("finding steam libraries...")
  sp = findPath()
  log.debug(sp)
  vp = sp + r"\config\config.vdf"
  log.debug(vp)

  f = open(vp, "r")
  cvdf = f.read()
  f.close()

  matches = re.finditer(bifExp, cvdf)
  libs = [sp]

  for matchNum, match in enumerate(matches, start=1):
    log.debug("Match {matchNum} was found at {start}-{end}: {match}".format(
        matchNum=matchNum,
        start=match.start(),
        end=match.end(),
        match=match.group()))

    for groupNum in range(0, len(match.groups())):
      groupNum = groupNum + 1
      m = match.group(groupNum)

      log.debug("Group {groupNum} found at {start}-{end}: {group}".format(
          groupNum=groupNum,
          start=match.start(groupNum),
          end=match.end(groupNum),
          group=m))
      libs.append(m)

  for i, lib in enumerate(libs):
    libs[i] = lib.replace(r"\\", os.sep)

  return libs


# finds tf2's /tf/ path
def findGame():
  global gameLibrary
  global gamePath
  global gameDir

  if gamePath != "":
    return gamePath

  libs = findLibraries()
  log.debug(libs)

  found = False
  for lib in libs:
    if found:
      break

    exists = True
    for gf in gameFiles:
      if not os.path.exists(lib + gf):
        exists = False
        break

    if exists:
      gameLibrary = lib
      found = True
      break

  gamePath = gameLibrary + gameDir
  log.debug(gamePath)
  return gamePath


# moves /tf/cfg/ and /tf/custom/ to /tf/backup_before_default/{date}
def backupUserConfig():
  global gamePath

  if gamePath == "":
    findGame()

  backupPath = gamePath + "backup_before_default\\{date}".format(
      date=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

  os.makedirs(backupPath, exist_ok=True)

  log.debug(gamePath)
  shutil.move(gamePath + "cfg", backupPath + "\\cfg")
  shutil.move(gamePath + "custom", backupPath + "\\custom")
  return backupPath


# gets the path where steam cloud is stored for the current user
def getCurrentUserPath():
  global steamPath
  log.debug("Disabling steam cloud for TF2")

  if steamPath == "":
    findPath()

  luf = open(steamPath + "\\config\\loginusers.vdf", "r+")
  loginUsers = luf.read()
  luf.close()

  recentPos = 0

  # m = loginUsers.find(r"\"mostrecent\"[\s]+\"(1)\"", recentPos)
  matches = re.finditer(r"\"mostrecent\"[\s]+\"(1)\"", loginUsers)

  for matchNum, match in enumerate(matches, start=1):
    log.debug("Match {matchNum} was found at {start}-{end}: {match}".format(
        matchNum=matchNum,
        start=match.start(),
        end=match.end(),
        match=match.group()))

    for groupNum in range(0, len(match.groups())):
      groupNum = groupNum + 1
      m = match.group(groupNum)

      log.debug("Group {groupNum} found at {start}-{end}: {group}".format(
          groupNum=groupNum,
          start=match.start(groupNum),
          end=match.end(groupNum),
          group=m))

      recentPos = match.start(groupNum)
      loginUsers = loginUsers[0:recentPos]

      lookForQuote = False
      closePos = 0
      openPos = 0
      bopen = False

      steamID = ""
      while steamID == "":
        recentPos -= 1
        if loginUsers[recentPos] == '{':
          lookForQuote = True
        elif lookForQuote:
          if loginUsers[recentPos] == '"':
            if bopen:
              openPos = recentPos + 1
              steamID = loginUsers[openPos:closePos]
            elif not bopen:
              closePos = recentPos  # - 1
              bopen = True

      id32 = int(steamID) - 76561197960265728
      userdata = steamPath + "\\userdata\\"
      log.debug(userdata + str(id32))
      if not os.path.exists(userdata + str(id32)):
        id32 -= 1

      return userdata + str(id32)


# set files empty at tf2's cloud storage
def disableCloud():
  p = getCurrentUserPath()
  cdir = p + "\\440\\remote"
  log.debug("TF2's steam cloud dir: {ud}".format(ud=cdir))

  for root, _dirs, files in os.walk(cdir, topdown=False):
    for name in files:
      log.debug("cleaning file: {f}".format(f=name))
      open(os.path.join(root, name), "w").close()


# runs the game's validation and waits for tf/cfg, tf/cfg/config_default.cfg, tf/custom, tf/custom/workshop and tf/custom/readme.txt
def validateGameFiles():
  global gamePath
  webbrowser.open("steam://validate/440")

  while True:
    time.sleep(5)
    if os.path.exists(gamePath + "cfg") and os.path.exists(
        gamePath + "custom"
    ) and os.path.exists(gamePath + "custom\\workshop") and os.path.exists(
        gamePath +
        "cfg\\config_default.cfg") and os.path.exists(gamePath +
                                                      "custom\\readme.txt"):
      log.debug("Found the default config files")
      break
    else:
      log.debug(
          "Waiting for config files to finish verification and download...")


# runs tf2's autoconfig and then quits, dxlevel can be included
def autoConfig(mode="reset", dxlevel=""):
  log.debug("autoconfig %s" % dxlevel)
  dxl = ""
  if dxlevel != "":
    dxl = "-dxlevel {dxl} ".format(dxl=dxlevel)

  if mode == "reset":
    webbrowser.open(
        "steam://rungameid/440//-novid -default -autoconfig +host_writeconfig +mat_savechanges +quit"
        .format(dxl=dxl))
  else:
    webbrowser.open("steam://rungameid/440//{dxl}-novid +quit".format(dxl=dxl))

  time.sleep(10)
  while True:
    time.sleep(5)
    p = getTF2Process()
    if p == None:
      log.debug("tf2 closed, continuing")
      break
    else:
      log.debug("waiting tf2 to close")


# modifies or adds launch options for tf2
# steam must be closed before modifying the file as it only reads the changes on start
def setLaunchOptions(lopts):
  p = getCurrentUserPath()
  lcPath = "{p}\\config\\localconfig.vdf".format(p=p)
  log.debug(lcPath)
  f = open(lcPath, "r+", encoding="utf8")
  data = str(f.read())
  f.close()

  r440 = r"\"Steam\"[\s]+{[\s\S]+?\"Apps\"[\s]+?{[\s\S]+?[\"440\"][\s]+{?([\s\S]+?)}"
  matches = re.finditer(r440, data, re.MULTILINE)

  for matchNum, match in enumerate(matches, start=1):
    log.debug("Match {matchNum} was found at {start}-{end}: {match}".format(
        matchNum=matchNum,
        start=match.start(),
        end=match.end(),
        match=match.group()))
    for groupNum in range(0, len(match.groups())):
      groupNum = groupNum + 1

      log.debug("Group {groupNum} found at {start}-{end}: {group}".format(
          groupNum=groupNum,
          start=match.start(groupNum),
          end=match.end(groupNum),
          group=match.group(groupNum)))

      start = match.start(groupNum)
      end = match.end(groupNum)
      loidx = data.find("LaunchOptions", start, end)

      p = getSteamProcess()
      p.terminate()
      p.wait()
      time.sleep(5)

      f = open(lcPath, "w", encoding="utf8")
      if loidx == -1:
        lo = '\n   "LaunchOptions"   "' + " ".join(lopts) + '"\n'
        f.write(data[0:start] + lo + data[start:len(data)])
      else:
        lor = r"\"LaunchOptions\"[\s]+\"(.*)\""
        modified = re.sub(
            lor, "\"LaunchOptions\"   \"{lo}\"".format(lo=" ".join(lopts)),
            data[start:end])
        log.debug("original: %s" % data[start:end])
        log.debug("modified: %s" % modified)
        f.write(data[0:start] + modified + data[end:len(data)])
      f.close()

      webbrowser.open("steam://open/games")
