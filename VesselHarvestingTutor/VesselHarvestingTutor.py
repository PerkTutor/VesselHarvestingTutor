import os
import unittest
import vtk, qt, ctk, slicer
import time
from slicer.ScriptedLoadableModule import *
from vtk import vtkMath
import logging
import time, datetime
import math, numpy
import csv

NUM_MODELS = 9

#
# VesselHarvestingTutor
#

class VesselHarvestingTutor(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Vessel Harvesting Tutor" 
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Perk Lab"] 
    self.parent.helpText = """ This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """  This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
    """ # replace with organization, grant and thanks.

#
# VesselHarvestingTutorWidget
#

class VesselHarvestingTutorWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.runTutor = False
    self.cutterFiducial = slicer.modules.markups.logic().AddFiducial()
    # Instantiate and connect widgets ...

    #
    # EVH Tutor Accordion
    #
    evhTutorCollapsibleButton = ctk.ctkCollapsibleButton()
    evhTutorCollapsibleButton.text = "Endovein Harvesting Tutor"
    self.layout.addWidget(evhTutorCollapsibleButton)
    evhTutorFormLayout = qt.QFormLayout(evhTutorCollapsibleButton)

    # Checkbox to indicate if user is a novice or expert 
    self.noviceCheckbox = qt.QRadioButton("Novice User")
    self.noviceCheckbox.connect('toggled(bool)', self.setNoviceExperience)
    self.expertCheckbox = qt.QRadioButton("Expert User")
    self.expertCheckbox.connect('toggled(bool)', self.setExpertExperience)
    evhTutorFormLayout.addRow(self.noviceCheckbox, self.expertCheckbox)

    # Button to start recording with EVH tutor
    self.runTutorButton = qt.QPushButton("Start Recording")
    self.runTutorButton.toolTip = "Starts EVH tutor and recording practice procedure."
    self.runTutorButton.enabled = True
    self.runTutorButton.connect('clicked(bool)', self.onRunTutorButton)
    evhTutorFormLayout.addRow(self.runTutorButton)

    # Smallest angle between retractor and vessel axis
    self.minAngleDescriptionLabel = qt.QLabel("Smallest Angle Between Retractor and Vessel:")
    self.minAngleDescriptionLabel.setVisible(False)
    self.minAngleValueLabel = qt.QLabel("0")
    self.minAngleValueLabel.setVisible(False)
    self.minAngleValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.minAngleDescriptionLabel, self.minAngleValueLabel)

    # Maximum angle between retractor and vessel axis
    self.maxAngleDescriptionLabel = qt.QLabel("Largest Angle Between Retractor and Vessel:")
    self.maxAngleDescriptionLabel.setVisible(False)
    self.maxAngleValueLabel = qt.QLabel("0")
    self.maxAngleValueLabel.setVisible(False)
    self.maxAngleValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.maxAngleDescriptionLabel, self.maxAngleValueLabel)

    # Minimum distance from vessel
    self.minDistanceDescriptionLabel = qt.QLabel("Shortest Distance Cut from Dissected Vein:")
    self.minDistanceDescriptionLabel.setVisible(False)
    self.minDistanceValueLabel = qt.QLabel("0")
    self.minDistanceValueLabel.setVisible(False)
    self.minDistanceValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.minDistanceDescriptionLabel, self.minDistanceValueLabel)

    # Maximum distance from vessel
    self.maxDistanceDescriptionLabel = qt.QLabel("Largest Distance Cut from Dissected vein:")
    self.maxDistanceDescriptionLabel.setVisible(False)
    self.maxDistanceValueLabel = qt.QLabel("0")
    self.maxDistanceValueLabel.setVisible(False)
    self.maxDistanceValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.maxDistanceDescriptionLabel, self.maxDistanceValueLabel)

    # Average distance from vessel
    self.avgDistanceDescriptionLabel = qt.QLabel("Average Distance Cut from Dissected Vein:")
    self.avgDistanceDescriptionLabel.setVisible(False)
    self.avgDistanceValueLabel = qt.QLabel("0")
    self.avgDistanceValueLabel.setVisible(False)
    self.avgDistanceValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.avgDistanceDescriptionLabel, self.avgDistanceValueLabel)

    # Standard deviation of distance from vessel
    self.stdevDistanceDescriptionLabel = qt.QLabel("Standard Deviation of Distance Cut from Dissected Vein:")
    self.stdevDistanceDescriptionLabel.setVisible(False)
    self.stdevDistanceValueLabel = qt.QLabel("0")
    self.stdevDistanceValueLabel.setVisible(False)
    self.stdevDistanceValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.stdevDistanceDescriptionLabel, self.stdevDistanceValueLabel)

    # Slope of cutter's trajectory 
    self.trajectorySlopeDescriptionLabel = qt.QLabel("Slope of Linear Trajectory:")
    self.trajectorySlopeDescriptionLabel.setVisible(False)
    self.trajectorySlopeValueLabel = qt.QLabel("0")
    self.trajectorySlopeValueLabel.setVisible(False)
    self.trajectorySlopeValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.trajectorySlopeDescriptionLabel, self.trajectorySlopeValueLabel)

    # Time label of practice procedure
    self.procedureTimeDescriptionLabel = qt.QLabel("Total Procedure Time:")
    self.procedureTimeDescriptionLabel.setVisible(False)
    self.procedureTimeValueLabel = qt.QLabel("")
    self.procedureTimeValueLabel.setVisible(False)
    self.procedureTimeValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.procedureTimeDescriptionLabel, self.procedureTimeValueLabel)

    # Number of vessel branches cut
    self.numVesselsCutLabel = qt.QLabel("Number of successfully cut branches:")
    self.numVesselsCutLabel.setVisible(False)
    self.numVesselsCutValueLabel = qt.QLabel("")
    self.numVesselsCutValueLabel.setVisible(False)
    self.numVesselsCutValueLabel.setAlignment(0x0002) # Align right
    evhTutorFormLayout.addRow(self.numVesselsCutLabel, self.numVesselsCutValueLabel)

    # Button to display retractor trajectory 
    self.showPathButton = qt.QPushButton("Reconstruct retractor trajectory")
    self.showPathButton.toolTip = "Visualize retractor trajectory overlayed on vessel model."
    self.showPathButton.setVisible(False)
    self.showPathButton.enabled = True
    self.showPathButton.connect('clicked(bool)', self.onShowPathButton)
    evhTutorFormLayout.addRow(self.showPathButton)

    # Button to save metrics of practice EVH run
    self.saveButton= qt.QPushButton("Save metrics")
    self.saveButton.toolTip = "Save performance metrics to CSV file."
    self.saveButton.setVisible(False)
    self.saveButton.enabled = True
    self.saveButton.connect('clicked()', self.onSaveButton)
    evhTutorFormLayout.addRow(self.saveButton)

    # Button to reset EVH Tutor
    self.resetButton= qt.QPushButton("Reset EVH Tutor")
    self.resetButton.toolTip = "Reset vessel models and metrics."
    self.resetButton.enabled = True
    self.resetButton.connect('clicked(bool)', self.onResetTutorButton)
    evhTutorFormLayout.addRow(self.resetButton)

    # Add vertical spacing in EVH Tutor accordion 
    self.layout.addStretch(35)

    global logic 
    logic = VesselHarvestingTutorLogic()
    logic.loadTransforms()
    logic.loadModels()
    logic.resetModels()


  def setNoviceExperience(self):
    print "Experience level: Novice"
    self.experienceLevel = "Novice"


  def setExpertExperience(self):
    print "Experience level: Expert"
    self.experienceLevel = "Expert"


  def onResetTutorButton(self):
      logic.resetMetrics()
      logic.resetModels()
      # delete the path 
      pathModel = slicer.util.getNode('Path Trajectory')
      if pathModel: 
        slicer.mrmlScene.RemoveNode(pathModel)


  def onRunTutorButton(self):
    if not self.runTutor: # if tutor is not running, start it 
      #logic.runTutor = True
      self.onStartTutorButton()
    else: # stop active tutor 
      #logic.runTutor = False
      self.onStopTutorButton()


  def onStartTutorButton(self):
      self.onResetTutorButton()
      self.runTutorButton.setText("Stop Recording")
      self.runTutorButton.toolTip = "Stops EVH tutor and recording practice procedure."
      self.runTutor = not self.runTutor

      self.minAngleDescriptionLabel.setVisible(False)
      self.minAngleValueLabel.setVisible(False)

      self.maxAngleDescriptionLabel.setVisible(False)
      self.maxAngleValueLabel.setVisible(False)

      self.minDistanceDescriptionLabel.setVisible(False)
      self.minDistanceValueLabel.setVisible(False)

      self.maxDistanceDescriptionLabel.setVisible(False)
      self.maxDistanceValueLabel.setVisible(False)

      self.avgDistanceDescriptionLabel.setVisible(False)
      self.avgDistanceValueLabel.setVisible(False)

      self.stdevDistanceDescriptionLabel.setVisible(False)
      self.stdevDistanceValueLabel.setVisible(False)

      self.trajectorySlopeDescriptionLabel.setVisible(False)
      self.trajectorySlopeValueLabel.setVisible(False)

      self.procedureTimeDescriptionLabel.setVisible(False)
      self.procedureTimeValueLabel.setVisible(False)

      self.numVesselsCutLabel.setVisible(False)
      self.numVesselsCutValueLabel.setVisible(False)

      self.showPathButton.setVisible(False)
      self.saveButton.setVisible(False)

      self.startTime = time.time()

      global logic
      logic.tutorRunning = True 
  

  def onStopTutorButton(self):    
    self.runTutorButton.setText("Start Recording")
    self.runTutor = not self.runTutor
    
    global logic
    logic.tutorRunning = False 
    
    # Calculate total procedure time 
    stopTime = time.time() 
    timeTaken = logic.getTimestamp(self.startTime, stopTime)
    metrics = logic.getDistanceMetrics()

    self.minAngleDescriptionLabel.setVisible(True)
    self.minAngleValueLabel.setText(str(metrics['minAngle']) + ' degrees')
    self.minAngleValueLabel.setVisible(True)

    self.maxAngleDescriptionLabel.setVisible(True)
    self.maxAngleValueLabel.setText(str(metrics['maxAngle']) + ' degrees')
    self.maxAngleValueLabel.setVisible(True)

    self.minDistanceDescriptionLabel.setVisible(True)
    self.minDistanceValueLabel.setText(str(metrics['minDistance']))
    self.minDistanceValueLabel.setVisible(True)

    self.maxDistanceDescriptionLabel.setVisible(True)
    self.maxDistanceValueLabel.setText(str(metrics['maxDistance']))
    self.maxDistanceValueLabel.setVisible(True)

    self.avgDistanceDescriptionLabel.setVisible(True)
    self.avgDistanceValueLabel.setText(str(metrics['meanDistance']))
    self.avgDistanceValueLabel.setVisible(True)

    self.stdevDistanceDescriptionLabel.setVisible(True)
    self.stdevDistanceValueLabel.setText(str(metrics['stdDevCutDistances']))
    self.stdevDistanceValueLabel.setVisible(True)

    self.trajectorySlopeDescriptionLabel.setVisible(True)
    self.trajectorySlopeValueLabel.setText(str(metrics['trajectorySlope']))
    self.trajectorySlopeValueLabel.setVisible(True)

    self.procedureTimeValueLabel.setText(timeTaken)
    self.procedureTimeDescriptionLabel.setVisible(True)
    self.procedureTimeValueLabel.setVisible(True)

    self.numVesselsCutValueLabel.setText(str(metrics['branchesCut']))
    self.numVesselsCutLabel.setVisible(True)
    self.numVesselsCutValueLabel.setVisible(True)

    self.showPathButton.setVisible(True)
    self.saveButton.setVisible(True)


  def onShowPathButton(self):
    print 'Reconstructing retractor trajectory ...'
    fidNode = slicer.util.getNode('MarkupsFiducial_*')
    if fidNode == None:
      slicer.util.CreateNodeByClass('vtkMRMLMarkupsFiducialNode')
      fidNode = slicer.util.getNode('MarkupsFiducial_*')
    outputModel = slicer.mrmlScene.AddNode(slicer.vtkMRMLModelNode())
    outputModel.SetName('Path Trajectory')
    outputModel.CreateDefaultDisplayNodes()
    outputModel.GetDisplayNode().SetSliceIntersectionVisibility(True)
    outputModel.GetDisplayNode().SetColor(1,1,0)

    markupsToModel = slicer.mrmlScene.AddNode(slicer.vtkMRMLMarkupsToModelNode())
    markupsToModel.SetAutoUpdateOutput(True)
    markupsToModel.SetAndObserveModelNodeID(outputModel.GetID())
    markupsToModel.SetAndObserveMarkupsNodeID(fidNode.GetID())
    markupsToModel.SetModelType(slicer.vtkMRMLMarkupsToModelNode.Curve)
    markupsToModel.SetCurveType(slicer.vtkMRMLMarkupsToModelNode.CardinalSpline)
    print 'Reconstruction complete'

  
  def onSaveButton(self):
    timestamp = time.strftime("%H:%M:%S").replace(':', '-')
    filename = "C:/Users/christina/Documents/VesselHarvestingTutor/Data/Evh-Metrics-" + str(datetime.date.today()) + ' ' + timestamp + '.csv'
    metrics = logic.getDistanceMetrics()
    with open(filename, 'w+') as f:  
      writer = csv.writer(f, delimiter=',')
      writer.writerow(['Metric', 'Value']) 
      writer.writerow(['Experience', self.experienceLevel]) 
      for key, value in metrics.items():
        writer.writerow([key, value]) 
    print "Results successfully saved."


  def cleanup(self):
    pass


#
# VesselHarvestingTutorLogic
#

class VesselHarvestingTutorLogic(ScriptedLoadableModuleLogic):

  
  def __init__(self):
    self.resetMetrics()
    self.tutorRunning = False
    self.modelPolydata = {}
    self.visiblePolydata = {}
    self.SKELETON_MODEL_NAME = 'Skeleton Model'
    self.lastCutTimestamp = time.time()


  def resetModels(self):
    print 'Resetting models'
    for i in range(0, NUM_MODELS):
      self.visiblePolydata['Model_' + str(i)] = True
    self.updateSkeletonModel()
    

  def resetMetrics(self):
    self.metrics = {
      'minDistance': float("inf"),
      'maxDistance': 0,
      'meanDistance': 0,
      'stdDevCutDistances': 0,
      'minAngle': 180,
      'maxAngle': 0,
      'trajectorySlope': 0,
      'branchesCut': 0,
      'cutDistances': []
    }
    self.branchStarts = []
    self.pathFiducialsX = []
    self.pathFiducialsY = []
    self.path = []
    self.lastTimestamp = time.time()
      
    # remove existing fiducials if they exist 
    fidNode = slicer.util.getNode('MarkupsFiducial_*')
    if fidNode != None:
      fidNode = slicer.util.getNode('MarkupsFiducial_*')
    slicer.mrmlScene.RemoveNode(fidNode)


  def loadTransforms(self):
    moduleDir = os.path.dirname(slicer.modules.vesselharvestingtutor.path)

    vesselToRetractor = slicer.util.getNode('VesselToRetractor')
    if vesselToRetractor == None:
      vesselToRetractor = slicer.vtkMRMLLinearTransformNode()
      vesselToRetractor.SetName('VesselToRetractor')
      slicer.mrmlScene.AddNode(vesselToRetractor)
    
    vesselModelToVessel = slicer.util.getNode('VesselModelToVessel') 
    if vesselModelToVessel == None: 
      vesselModelToVessel = slicer.vtkMRMLLinearTransformNode()
      vesselModelToVessel.SetName('VesselModelToVessel')
      slicer.mrmlScene.AddNode(vesselModelToVessel)
    vesselModelToVessel.SetAndObserveTransformNodeID(vesselToRetractor.GetID())

    triggerToCutter = slicer.util.getNode('TriggerToCutter')
    if triggerToCutter == None:
      triggerToCutter = slicer.vtkMRMLLinearTransformNode()
      triggerToCutter.SetName('TriggerToCutter')
      slicer.mrmlScene.AddNode(triggerToCutter)
    
    cutterToRetractor = slicer.util.getNode('CutterToRetractor')
    if cutterToRetractor == None:
      cutterToRetractor = slicer.vtkMRMLLinearTransformNode()
      cutterToRetractor.SetName('CutterToRetractor')
      slicer.mrmlScene.AddNode(cutterToRetractor)
    
    cutterMovingToTip = slicer.util.getNode('CutterMovingToCutterTip')
    if cutterMovingToTip == None:
      cutterMovingToTip = slicer.vtkMRMLLinearTransformNode()
      cutterMovingToTip.SetName('CutterMovingToCutterTip')
      slicer.mrmlScene.AddNode(cutterMovingToTip)
    
    cutterTipToCutter = slicer.util.getNode('CutterTipToCutter')
    if cutterTipToCutter == None:
      filePath = os.path.join(moduleDir, os.pardir, 'Transforms', 'CutterTipToCutter.h5')
      [success, cutterTipToCutter] = slicer.util.loadTransform(filePath, returnNode=True)
      cutterTipToCutter.SetName('CutterTipToCutter')

    cameraToRetractor = slicer.util.getNode('CameraToRetractor')
    if cameraToRetractor == None:
      filePath = os.path.join(moduleDir, os.pardir, 'Transforms', 'CameraToRetractor.h5')
      [success, cameraToRetractor] = slicer.util.loadTransform(filePath, returnNode=True)
      cameraToRetractor.SetName('CameraToRetractor')

    defaultSceneCamera = slicer.util.getNode('Default Scene Camera')
    cameraToRetractorID = cameraToRetractor.GetID()
    defaultSceneCamera.SetAndObserveTransformNodeID(cameraToRetractorID)

    cutterToRetractorID = cutterToRetractor.GetID()
    # Create and set fiducial point on the cutter tip, used to calculate distance metrics
    fidNode = slicer.util.getNode("F")
    fidNode.SetNthFiducialVisibility(0, 0)    
    fidNode.SetAndObserveTransformNodeID(cutterTipToCutter.GetID())

    cutterTipToCutter.SetAndObserveTransformNodeID(cutterToRetractorID)
    triggerToCutter.SetAndObserveTransformNodeID(cutterToRetractorID)
    cutterMovingToTip.SetAndObserveTransformNodeID(cutterTipToCutter.GetID())
    triggerToCutter.AddObserver(slicer.vtkMRMLLinearTransformNode.TransformModifiedEvent, self.updateTransforms)


  def loadModels(self):
    
    moduleDir = os.path.dirname(slicer.modules.vesselharvestingtutor.path)
    self.retractorModel= slicer.util.getNode('RetractorModel')
    if not self.retractorModel:
      modelFilePath = os.path.join(moduleDir, os.pardir,'CadModels', 'VesselRetractorHead.stl')
      [success, self.retractorModel] = slicer.util.loadModel(modelFilePath, returnNode=True)
      self.retractorModel.SetName('RetractorModel')
      self.retractorModel.GetDisplayNode().SetColor(0.9, 0.9, 0.9)
    
    self.cutterBaseModel = slicer.util.getNode('CutterBaseModel')
    if self.cutterBaseModel == None:
      modelFilePath = os.path.join(moduleDir, os.pardir, 'CadModels', 'CutterBaseModel.stl')
      [success, self.cutterBaseModel] = slicer.util.loadModel(modelFilePath, returnNode=True)
      self.cutterBaseModel.SetName('CutterBaseModel')
      self.cutterBaseModel.GetDisplayNode().SetColor(0.8, 0.9, 1.0)

    cutterTipToCutter = slicer.util.getNode('CutterTipToCutter')
    if cutterTipToCutter == None:
      logging.error('Load transforms before models!')
      return
    self.cutterBaseModel.SetAndObserveTransformNodeID(cutterTipToCutter.GetID())
    
    self.cutterMovingModel = slicer.util.getNode('CutterMovingModel')
    if self.cutterMovingModel == None:
      modelFilePath = os.path.join(moduleDir, os.pardir, 'CadModels', 'CutterMovingModel.stl')
      [success, self.cutterMovingModel] = slicer.util.loadModel(modelFilePath, returnNode=True)
      self.cutterMovingModel.SetName('CutterMovingModel')
      self.cutterMovingModel.GetDisplayNode().SetColor(0.8, 0.9, 1.0)

    cutterMovingToTip = slicer.util.getNode('CutterMovingToCutterTip')
    if cutterMovingToTip == None:
      logging.error('Load transforms before models!')
      return
    self.cutterMovingModel.SetAndObserveTransformNodeID(cutterMovingToTip.GetID())
	
    self.vesselModelToVessel = slicer.util.getNode('VesselModelToVessel')
    if not self.vesselModelToVessel:
      transformFilePath = os.path.join(moduleDir, os.pardir,'Transforms', 'VesselModelToVessel.h5')
      [success, self.vesselModelToVessel] = slicer.util.loadTransform(transformFilePath, returnNode=True)
      if success == False:
        logging.error('Could not read needle tip to needle transform!')
      else:
        self.vesselModelToVessel.SetName("VesselModelToVessel")
    vesselToRetractor = slicer.util.getNode('VesselToRetractor')
    
    vesselID = self.vesselModelToVessel.GetID()
    # get transform to world from vesselID
    vesselToWorld = self.vesselModelToVessel.GetTransformToParent()
    skeletonModel = slicer.util.getNode(self.SKELETON_MODEL_NAME)
    if skeletonModel == None: 
      skeletonModel = slicer.mrmlScene.AddNode(slicer.vtkMRMLModelNode())
      skeletonModel.SetName(self.SKELETON_MODEL_NAME)
      skeletonModel.CreateDefaultDisplayNodes()
      skeletonModel.GetDisplayNode().SetScalarVisibility(True)
      vesselModelToVessel = slicer.util.getNode('VesselModelToVessel') 
      skeletonModel.SetAndObserveTransformNodeID(vesselID)


    #load vessel
    appender = vtk.vtkAppendPolyData()
    self.vesselModel = slicer.util.getNode('Model_0')
    self.vesselModelToVesselID = slicer.util.getNode('VesselModelToVessel').GetID()
    self.branchStartsFiducialsNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLMarkupsFiducialNode')
    
    if not self.vesselModel: 
      for i in range(NUM_MODELS): 
        if i > 0: # load points for vessel branch
          fiducialFilename = 'Points_' + str(i) + '.fcsv'
          fiducialFilePath = os.path.join(moduleDir, os.pardir,'CadModels/vessel', fiducialFilename)
          slicer.util.loadMarkupsFiducialList(fiducialFilePath)
          fiducialNode = slicer.util.getNode('Points_' + str(i))
          world = [0,0,0]
          fiducialNode.GetNthFiducialPosition(0,world)
          self.branchStarts.append(world)
          self.branchStartsFiducialsNode.AddFiducial(world[0], world[1], world[2])
          self.branchStartsFiducialsNode.SetNthFiducialVisibility(i-1, 0) 
          fiducialNode.SetAndObserveTransformNodeID(self.vesselModelToVesselID)

        # load stl file for vessel branch 
        filename = 'Model_' + str(i) + '.stl' 
        filePath = os.path.join(moduleDir, os.pardir,'CadModels/vessel', filename)
        [success, vesselBranch] = slicer.util.loadModel(filePath, returnNode=True)
        poly = vesselBranch.GetPolyData()

        # set vessel color to red 
        colors = vtk.vtkIntArray()
        numPoints = poly.GetNumberOfPoints()
        colors.SetNumberOfValues(numPoints)
        for j in range(numPoints):
          colors.SetValue(j, 3) # 3 = red 
        poly.GetPointData().SetScalars(colors)
        
        self.modelPolydata['Model_' + str(i)] = poly
        self.visiblePolydata['Model_' + str(i)] = True 
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(vesselToWorld) # transform used here 
        transformFilter.SetInputData(poly)
        transformFilter.Update()
        appender.AddInputData(transformFilter.GetOutput())
        slicer.mrmlScene.RemoveNode(vesselBranch)
      appender.Update()
      skeletonModel.SetAndObservePolyData(appender.GetOutput()) 

      slicer.mrmlScene.AddNode(self.branchStartsFiducialsNode)
      fidNode = slicer.util.getNode("MarkupsFiducial_1")
      fidNode.SetName("Vessel Branch Starts")
      fidNode.SetAndObserveTransformNodeID(vesselID)

      # load fiducials to keep vessel model in camera view
      # load fiducials on vessel axis
      axisfiducialFilename = 'Vessel Axis.fcsv'
      axisfiducialFilePath = os.path.join(moduleDir, os.pardir,'CadModels/vessel', axisfiducialFilename)
      slicer.util.loadMarkupsFiducialList(axisfiducialFilePath)
      axisfiducialNode = slicer.util.getNode('Vessel Axis')
      axisfiducialNode.SetAndObserveTransformNodeID(self.vesselModelToVesselID)
      # load the reference 
      retractorfiducialFilename = 'Retractor Reference.fcsv'
      retractorfiducialFilePath = os.path.join(moduleDir, os.pardir,'CadModels/vessel', retractorfiducialFilename)
      slicer.util.loadMarkupsFiducialList(retractorfiducialFilePath)      


  def calculateVesselToRetractorAngle(self, vesselVector, retractorVector):
    angleRadians = vtk.vtkMath.AngleBetweenVectors(vesselVector[0:3], retractorVector[0:3])
    angleDegrees = round(vtk.vtkMath.DegreesFromRadians(angleRadians), 1)
    if self.metrics['maxAngle'] < angleDegrees:
      self.metrics['maxAngle'] = angleDegrees
    elif self.metrics['minAngle'] > angleDegrees:
      self.metrics['minAngle'] = angleDegrees
  
  
  def updateTransforms(self, event, caller):
    triggerToCutter = slicer.mrmlScene.GetFirstNodeByName('TriggerToCutter')    
    if triggerToCutter == None:
      logging.error('Could not found TriggerToCutter!')

    triggerToCutterTransform = triggerToCutter.GetTransformToParent()    
    angles = triggerToCutterTransform.GetOrientation()    

    shaftDirection_Cutter = [0,1,0]
    triggerDirection_Trigger = [1,0,0]
    triggerDirection_Cutter = triggerToCutterTransform.TransformFloatVector(triggerDirection_Trigger)    

    triggerAngle_Rad = vtk.vtkMath().AngleBetweenVectors(triggerDirection_Cutter, shaftDirection_Cutter)
    triggerAngle_Deg = vtk.vtkMath().DegreesFromRadians(triggerAngle_Rad)
    
    # adjusting values for openAngle calculation 
    if triggerAngle_Deg < 90.0:
      triggerAngle_Deg = 90.0
    if triggerAngle_Deg > 102.0:
      triggerAngle_Deg = 102.0

    openAngle = (triggerAngle_Deg - 90.0) * -2.2 # angle of cutter tip to shaft 
    #print "triggerAngle_Deg: " + str(triggerAngle_Deg), "open ", openAngle #DEBUG

    cutterMovingToTipTransform = vtk.vtkTransform()
    # By default transformations occur in reverse order compared to source code line order.
    # Translate center of rotation back to the original position
    cutterMovingToTipTransform.Translate(0,0,-20)
    # Rotate cutter moving part
    cutterMovingToTipTransform.RotateY(openAngle)
    # Translate center of rotation of the moving part to origin
    cutterMovingToTipTransform.Translate(0,0, 20)
    
    cutterMovingToTip = slicer.mrmlScene.GetFirstNodeByName('CutterMovingToCutterTip')
    cutterMovingToTip.SetAndObserveTransformToParent(cutterMovingToTipTransform)   

    # current timestamp is time.time()
    # save fiducial point and update model polydata every 0.25 seconds 
    if (time.time() - self.lastTimestamp) > 0.25 and self.tutorRunning: 
      self.updateSkeletonModel()
      cutterTipWorld = [0,0,0,0]
      fiducial = slicer.util.getNode("F")
      fiducial.GetNthFiducialWorldCoordinates(0,cutterTipWorld) # z coordinate not important for linear slope calculation

      # add path fiducials to separate node
      self.pathFiducialsNode = slicer.util.getNode('MarkupsFiducial_*')
      if self.pathFiducialsNode == None:
        self.pathFiducialsNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLMarkupsFiducialNode')
        slicer.mrmlScene.AddNode(self.pathFiducialsNode)
      slicer.modules.markups.logic().AddFiducial(cutterTipWorld[0], cutterTipWorld[1], cutterTipWorld[2])
      # set new fiducial's label and hide from 3D view
      n = self.pathFiducialsNode.GetNumberOfFiducials() - 1
      self.pathFiducialsNode.SetNthFiducialLabel(n, str(n))
      self.pathFiducialsNode.SetNthFiducialVisibility(n, 0)  

      self.pathFiducialsX.append(cutterTipWorld[0])
      self.pathFiducialsY.append(cutterTipWorld[1])
      self.path.append(cutterTipWorld[:-1])
      self.lastTimestamp = time.time()

      self.updateAngleMetrics()
      if math.fabs(openAngle) < 0.25 and self.tutorRunning and self.lastTimestamp - self.lastCutTimestamp > 3:
        self.lastCutTimestamp = time.time()
        self.checkModel()


  def getClosestBranch(self, cutLocation):
    branchNum = 0
    minDistance = float("inf")
    numBranches = NUM_MODELS -1
    for i in range(numBranches):
      RAScoordinates = [0,0,0,0]
      self.branchStartsFiducialsNode.GetNthFiducialWorldCoordinates(i,RAScoordinates)
      print cutLocation
      p = RAScoordinates[:-1]
      distance = math.sqrt(vtkMath.Distance2BetweenPoints(cutLocation, p))
      if distance < minDistance:
        minDistance = distance
        branchNum = i + 1
    '''
    for i in range(NUM_MODELS - 1):
      index = i + 1
      modelName = 'Model_' + str(index)
      if self.visiblePolydata[modelName]:
        poly = self.modelPolydata[modelName]
        n = poly.GetNumberOfPoints()
        for j in range(0, n, 15): # DEBUG reove the 15 and dropped fiducial 
          p = poly.GetPoint(j)
          distance = math.sqrt(vtkMath.Distance2BetweenPoints(cutLocation, p))
          # add fiducial 
          slicer.modules.markups.logic().AddFiducial(p[0], p[1], p[2])
          if distance < minDistance:
            minDistance = distance
            branchNum = index
          if distance < branchMin: # DEBUG
            branchMin = distance
            p = poly.GetPoint(j) #DEBUG
        print 'distance to branch ', index, ': ', branchMin, ' closest point from branch ', p

      branchMin, p = float("inf"), () # DEBUG
    print '\n', 'Distance to closest branch: ', minDistance, ', closest branch number: ', branchNum
    '''
    return minDistance, branchNum


  def checkModel(self): # check if vessel branch needs to be snipped  
    removebranch = ""     
    cutterTip = slicer.util.getNode("CutterMovingModel")
    branchNum = 0 # tracks which vessel should be cut if applicable 

    cutterTipWorld = [0,0,0,0]
    fiducial = slicer.util.getNode("F")
    fiducial.GetNthFiducialWorldCoordinates(0,cutterTipWorld) # Get point on cutter tip 
    cutLocation = (cutterTipWorld[0], cutterTipWorld[1], cutterTipWorld[2])
    self.lastCutTimestamp = time.time()
    # finds closest branch to be cut 
    minDistance, branchNum = self.getClosestBranch(cutLocation)
     
    if branchNum != 0: # block deletion of the main vessel 
      vesselAxis = self.modelPolydata['Model_0']
      n = vesselAxis.GetNumberOfPoints()
      distanceToAxis = float('inf')
      for i in range(n):
        distance = math.sqrt(vtkMath.Distance2BetweenPoints(cutLocation, vesselAxis.GetPoint(i)))
        if distance < distanceToAxis:
          distanceToAxis = distance
      if minDistance < 280: 
        removeBranch = 'Model_' + str(branchNum)
        print 'Removing branch ' + str(branchNum)
        self.visiblePolydata[removeBranch] = False
        self.updateSkeletonModel()
        self.metrics['cutDistances'].append(distanceToAxis)
     

  def npArrayFromVtkMatrix(self, vtkMatrix):
    npArray = numpy.zeros((4,4))
    for row in range(4):
      for column in range(4):
          npArray[row][column] = vtkMatrix.GetElement(row,column)
    return npArray

    
  def updateAngleMetrics(self):
    vesselModelToVessel = slicer.mrmlScene.GetFirstNodeByName('VesselModelToVessel')  
    vesselToRas = vtk.vtkMatrix4x4()
    vesselModelToVessel.GetMatrixTransformToWorld(vesselToRas)
    vesselDirection = numpy.dot(self.npArrayFromVtkMatrix(vesselToRas), numpy.array([ 0, 0, 1, 0]))

    cutterTipToCutter = slicer.mrmlScene.GetFirstNodeByName('CutterTipToCutter')  
    cutterToRas = vtk.vtkMatrix4x4()
    cutterTipToCutter.GetMatrixTransformToWorld(cutterToRas)
    cutterDirection = numpy.dot(self.npArrayFromVtkMatrix(cutterToRas), numpy.array([ 0, 0, 1, 0]))

    self.calculateVesselToRetractorAngle(vesselDirection, cutterDirection)
        
  
  def getDistanceMetrics(self): 
    if len(self.metrics['cutDistances']) == 0:
      self.metrics['cutDistances'] = [0]
    self.metrics['minDistance'] = round(min(self.metrics['cutDistances']), 2)
    self.metrics['maxDistance'] = round(max(self.metrics['cutDistances']), 2)
    self.metrics['meanDistance'] = round(sum(self.metrics['cutDistances']) / len(self.metrics['cutDistances']), 2)
    self.metrics['stdDevCutDistances'] = round(numpy.array(self.metrics['cutDistances']).std(), 2)
    for key in self.visiblePolydata:
      if not self.visiblePolydata[key]:
        self.metrics['branchesCut'] += 1
    if len(self.pathFiducialsX) > 0:
      x = numpy.array(self.pathFiducialsX)
      y = numpy.array(self.pathFiducialsY)
      # x and y points used to compute slope of linear trajectory
      A = numpy.vstack([x, numpy.ones(len(x))]).T
      slope, _ = numpy.linalg.lstsq(A, y)[0]
      self.metrics['trajectorySlope'] = round(slope, 2)
      self.metrics['points'] = self.path
    return self.metrics


  def getTimestamp(self, start, stop):
    elapsed = stop - start 
    formattedTime = time.strftime('%H:%M:%S', time.gmtime(elapsed)) # convert seconds to HH:MM:SS timestamp
    return formattedTime
    

  def updateSkeletonModel(self):
    appender = vtk.vtkAppendPolyData()
    '''
    vesselToWorld = vtk.vtkGeneralTransform()
    self.vesselModelToVessel.GetTransformToWorld(vesselToWorld)
    '''
    vesselToWorld = self.vesselModelToVessel.GetTransformToParent()
    for name, visiblilityFlag in self.visiblePolydata.iteritems():
      if visiblilityFlag:
        poly = self.modelPolydata[name]
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(vesselToWorld)
        transformFilter.SetInputData(poly)
        transformFilter.Update()
        transformedPoly = transformFilter.GetOutput()
        appender.AddInputData(transformedPoly)
        self.modelPolydata[name] = transformedPoly
    appender.Update()
    modelNode = slicer.util.getFirstNodeByName(self.SKELETON_MODEL_NAME)
    if modelNode is None:
      logging.error("Model node not found: {0}".format(self.SKELETON_MODEL_NAME))
    modelNode.SetAndObservePolyData(appender.GetOutput())  
    # TODO: how to get transformed polydata out to update self.modelPolydatas?


class VesselHarvestingTutorTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_VesselHarvestingTutor1()


  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)


  def test_VesselHarvestingTutor1(self):
    logic = VesselHarvestingTutorLogic()
    logic.loadTransforms()
    logic.loadModels()

