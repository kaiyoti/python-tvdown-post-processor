import argparse
import sys
import logging
import os.path
import time
import re
import shutil
import os
from pyunpack import Archive

class UnrarUtil:
  # This prevents sample files from being extracted with a limite
  # that all files must be greater than 60 mb to be extracted
  extractSizeLimit = 60000000
  isArchive = True
  isSeeding = True
  
  def __init__ (self, inputFile=None, outputName=None, dir=None):
    self.logging = False
    self.debug = False

    if inputFile is None:
      sys.exit("Error: inputFile file/folder needs to be specified!");

    self.inputFile = inputFile
    self.outputName = outputName

    if dir is None:
      ready_dir = os.environ.get('TV_READY_DIR')
      if ready_dir is None:
        sys.exit("Output directory not defined AND TV_READY_DIR environment variable not set")
      
    self.dir = ready_dir

    temp_dir = os.environ.get('TV_TEMP_DIR')
    if temp_dir is None:
      temp_dir = os.environ.get('HOME') + "/tmp/"
    self.tempRootPath = temp_dir

    if self.debug == True:
      print ("Initialization: inputFile = %s" % inputFile)
      print ("Initialization: OutputName = %s" % outputName)

  def enableLogging(self, logFile=None):
    if logFile is None:
      sys.exit("Specify a log file")
    else:
      self.log = logFile
      self.logging = True
      if self.debug == True:
        print ("Logging enabled using log: %s" % self.log)

  def validateInputs(self):
    # Check if input file exists
    if os.path.isfile(self.inputFile) == False:
      if os.path.isdir(self.inputFile) == True:
        self.inputFile = self.searchForRarFile()
      else:
        sys.exit("No valid archive, video, or directory specified")

    # See if we are seeding
    if "/seed/" not in self.inputFile:
      isSeeding = False

    # Check if the output file name is empty or does not contain "---"
    if self.outputName is None or "---" not in self.outputName:
      print ('"%s" is empty or does not contain valid name, attempting to use directory name' % self.outputName)
      name_search = self.inputFile.split("[-]")
      if len(name_search) < 3:
        print ('No valid name found in the directory path... please specify a valid output filename')
      else:
        print ('"%s" will be used as the target filename' % name_search[1])
        self.outputName = name_search[1]

  def searchForRarFile(self):
    command='find "{}" -regextype posix-extended -regex "^.*\.part(0)*1\.rar"'.format(self.inputFile)
    output = os.popen(command, "r")
    find_result = output.readline().rstrip('\n')
    if not find_result:
      # No valid rar file, try to search for video file
      print("No valid rar archive found in the directory")
      find_result = self.searchVideoFile(self.inputFile)
      if not find_result:
        # Really tried and found nothing, time to quit
        sys.exit("Input directory contains no video content, existing...")
      else:
        self.isArchive = False

    return find_result

  def getOrCreateTempDir(self):
    # Construct a temporary path
    millis = int(round(time.time() * 1000))
    clean_name = re.sub(r'[^\w]', '', self.outputName)
    temp_full_path = self.tempRootPath + str(millis) + clean_name
    print ("Creating temporary directory: %s" % temp_full_path)
    if not os.path.exists(temp_full_path):
      os.makedirs(temp_full_path)
    return temp_full_path

  def extractFile(self, tempPath=None):
    if tempPath is None:
      sys.exit("You must specify a path for extracting to temp location")
    # Hide all the rar extraction output
    hideRarOutputArg = ' -inul'
    #hideRarOutputArg = ''

    # Rar size limit, only extract files larger than 60mb
    sizeLimitArg = ' -sm' + str(self.extractSizeLimit)

    # Using the nix command line unrar because it's more flexible (IMO)
    command = 'unrar x{}{} "{}" {}'.format(hideRarOutputArg, sizeLimitArg, self.inputFile, tempPath)
    print('Executing command: {}'.format(command))
    os.system(command)

    # Search for video file
    videoFile = self.searchVideoFile(tempPath)
    if videoFile is None:
      print("No video file found in the extraction")
      self.dumpRarContents()
      sys.exit("Error Exit!")
    return videoFile

  def dumpRarContents(self):
    command = 'unrar l "{}"'.format(self.inputFile)
    print("Dumping rar file contents: ")
    os.system(command)

  def searchVideoFile(self, tempPath=None):
    # Try to search mp4, mkv, or avi file
    command = 'find {} -name "*.mp4" -o -name "*.mkv" -o -name "*.avi"'.format(tempPath)
    print command
    p = os.popen(command, "r")
    find_result = p.readline()
    sys.stdout.write('Video result: {}'.format(find_result))

    # strip new line character when returning
    return find_result.rstrip('\n')

  def moveVideoToTargetDir(self, videoPath, copy=False):
    # Check if file already exists at the target directory
    filename, file_extension = os.path.splitext(videoPath)
    target_filename = '{}{}{}'.format(self.dir, self.outputName, file_extension)
    print 'Target filename: "{}"'.format(target_filename)

    if copy == False:
      shutil.move(videoPath, target_filename)
    else:
      shutil.copy(videoPath, target_filename)

  def deleteTempDir(self, tempPath=None):
    if tempPath is not None and os.path.exists(tempPath):
      print ("Cleaning temp directory: %s" % tempPath)
      shutil.rmtree(tempPath)

  def process(self):
    # Validate our inputs
    self.validateInputs()

    if self.isArchive == True:
      # Create a temp path
      tempPath = self.getOrCreateTempDir()

      # All Set! Time to perform extraction
      videoFile = self.extractFile(tempPath)
      self.moveVideoToTargetDir(videoFile, False)

      # Clean up the temporary directory
      self.deleteTempDir(tempPath)
    else:
      self.moveVideoToTargetDir(self.inputFile, self.isSeeding)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Utility to unrar a file, search and rename a video file')
  parser.add_argument('input', help='Input rar/video file name or dir')
  parser.add_argument('-o', '--output', help='Video file name of the result file', required=False)
  parser.add_argument('-d', '--dir', help='Resulting directory where video will copied to', required=False)
  parser.add_argument('-l', '--log', help='Log file to log output to', required=False)
  args = parser.parse_args()

  # Create instance of unrar util
  unrarUtil = UnrarUtil(args.input, args.output, args.dir);

  # Enabling logging if specified
  if args.log is not None:
    unrarUtil.enableLogging(args.log);

  # Process the rar file
  unrarUtil.process();
