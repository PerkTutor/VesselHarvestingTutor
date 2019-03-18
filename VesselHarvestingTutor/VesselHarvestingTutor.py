import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from vtk import vtkMath
import logging
import time, datetime
import math, numpy
import csv

NUM_BRANCHES = 10
NUM_MODELS = 11
ENDRANGE = 12

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
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
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
    self.saveButton.connect('clicked(bool)', self.onSaveButton)
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
    logic.runTutor = False
    logic.loadTransforms()
    logic.loadModels()
    logic.resetModels()


  def onResetTutorButton(self):
      logic.resetMetrics()
      logic.resetModels()
      
      # delete the path 
      pathModel = slicer.util.getNode('Path Trajectory')
      if pathModel: 
        slicer.mrmlScene.RemoveNode(pathModel)


  def onRunTutorButton(self):
    if not self.runTutor: # if tutor is not running, start it 
      logic.runTutor = True
      self.onStartTutorButton()
    else: # stop active tutor 
      logic.runTutor = False
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

      self.trajectorySlopeDescriptionLabel.setVisible(False)
      self.trajectorySlopeValueLabel.setVisible(False)

      self.procedureTimeDescriptionLabel.setVisible(False)
      self.procedureTimeValueLabel.setVisible(False)

      self.showPathButton.setVisible(False)
      self.saveButton.setVisible(False)

      self.startTime = time.time()
  

  def onStopTutorButton(self):    
    self.runTutorButton.setText("Start Recording")
    self.runTutor = not self.runTutor
    
    logic.runTutor = False
    
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

    self.trajectorySlopeDescriptionLabel.setVisible(True)
    self.trajectorySlopeValueLabel.setText(str(metrics['trajectorySlope']))
    self.trajectorySlopeValueLabel.setVisible(True)

    self.procedureTimeValueLabel.setText(timeTaken)
    self.procedureTimeDescriptionLabel.setVisible(True)
    self.procedureTimeValueLabel.setVisible(True)

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
    filename = "C:/Users/perk/VesselHarvesting/VesselHarvestingTutor/Data/Evh-Metrics-" + str(datetime.date.today()) + '.csv'
    metrics = logic.getDistanceMetrics()
    with open(filename, 'w+') as f:  
      writer = csv.writer(f, delimiter=',')
      writer.writerow(['Metric', 'Value']) 
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
    self.branchStarts = []
    self.modelPolydata = {}
    self.visiblePolydata = {}
    self.SKELETON_MODEL_NAME = 'Skeleton Model'


  def resetModels(self):
    for i in range(0, NUM_MODELS):
      branchNode = slicer.util.getNode('Model_' + str(i))
      if branchNode:
        branchNode.GetDisplayNode().SetVisibility(True)
    

  def resetMetrics(self):
    self.metrics = {
      'minDistance': float("inf"),
      'maxDistance': 0,
      'minAngle': 180,
      'maxAngle': 0,
      'trajectorySlope': 0
    }
    self.pathFiducialsX = []
    self.pathFiducialsY = []
    self.path = []
    self.lastTimestamp = time.time()
    self.runTutor = False    
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

    stylusTipToStylus = slicer.util.getNode('StylusTipToStylus')
    if stylusTipToStylus == None:
      filePath = os.path.join(moduleDir, os.pardir, 'Transforms', 'StylusTipToStylus.h5')
      [success, stylusTipToStylus] = slicer.util.loadTransform(filePath, returnNode=True)
      stylusTipToStylus.SetName('StylusTipToStylus')

    # TODO debug this 
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
    stylusTipToStylus.SetAndObserveTransformNodeID(cutterToRetractorID)


  def loadModels(self):
    
    moduleDir = os.path.dirname(slicer.modules.vesselharvestingtutor.path)

    """     
    for i in range(NUM_MODELS):  
      fiducialFilename = 'Points_' + str(i) + '.fcsv'
      fiducialFilePath = os.path.join(moduleDir, os.pardir,'CadModels/vessel', fiducialFilename)
      slicer.util.loadMarkupsFiducialList(fiducialFilePath)
      fiducialNode = slicer.util.getNode('Points_' + str(i))         

      # create models
      outputModel = slicer.mrmlScene.AddNode(slicer.vtkMRMLModelNode())
      outputModel.CreateDefaultDisplayNodes()
      outputModel.SetName('Model_' + str(i))
      outputModel.GetDisplayNode().SetSliceIntersectionVisibility(True)
      outputModel.GetDisplayNode().SetColor(1,0,0)
      self.modelPolydata['Model_' + str(i)] = outputModel.GetPolyData()

      markupsToModel = slicer.mrmlScene.AddNode(slicer.vtkMRMLMarkupsToModelNode())
      markupsToModel.SetAutoUpdateOutput(True)
      markupsToModel.SetAndObserveModelNodeID(outputModel.GetID())
      markupsToModel.SetAndObserveMarkupsNodeID(fiducialNode.GetID())
      markupsToModel.SetModelType(slicer.vtkMRMLMarkupsToModelNode.Curve)
      markupsToModel.SetCurveType(slicer.vtkMRMLMarkupsToModelNode.CardinalSpline)

      if i == 0:
        self.vesselModel = outputModel
        markupsToModel.SetTubeRadius(5)
      else:
        markupsToModel.SetTubeRadius(2)



    # initialize array with first point of each branch
    for i in range(1, NUM_MODELS):
      temp = slicer.util.getNode('Points_' + str(i))
      world = [0,0,0,0]
      temp.GetNthFiducialWorldCoordinates(0, world) 
      self.branchStarts.append(world)
    """
    self.retractorModel= slicer.util.getNode('RetractorModel')
    if not self.retractorModel:
      modelFilePath = os.path.join(moduleDir, os.pardir,'CadModels', 'VesselRetractorHead.stl')
      [success, self.retractorModel] = slicer.util.loadModel(modelFilePath, returnNode=True)
      self.retractorModel.SetName('RetractorModel')
      self.retractorModel.GetDisplayNode().SetColor(0.9, 0.9, 0.9)
    # set model under stylusTipToStylus transform 
    stylusTipToStylus = slicer.util.getNode('StylusTipToStylus')
    if stylusTipToStylus:      
      stylusID = stylusTipToStylus.GetID()
      self.retractorModel.SetAndObserveTransformNodeID(stylusID)
    
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

    #load vessel
    appender = vtk.vtkAppendPolyData()
    self.vesselModel = slicer.util.getNode('Model_3')
    if not self.vesselModel: 
      for i in range(NUM_MODELS):  
        # load stl file for vessel branch 
        filename = 'Model_' + str(i) + '.stl' 
        filePath = os.path.join(moduleDir, os.pardir,'CadModels/vessel', filename)
        [success, vesselBranch] = slicer.util.loadModel(filePath, returnNode=True)
        poly = vesselBranch.GetPolyData()

        # set vessel color to red 
        colors = vtk.vtkIntArray()
        numPoints = poly.GetNumberOfPoints()
        colors.SetNumberOfValues(numPoints)
        for i in range(numPoints):
          colors.SetValue(i, 3)
        poly.GetPointData().SetScalars(colors)
        
        self.modelPolydata['Model_' + str(i)] = poly
        self.visiblePolydata['Model_' + str(i)] = True # TODO improve representation for efficiency 
        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(vesselToWorld) # transform used here 
        transformFilter.SetInputData(poly)
        transformFilter.Update()
        appender.AddInputData(transformFilter.GetOutput())
      appender.Update()
      skeletonModel.SetAndObservePolyData(appender.GetOutput())  
  
  def calculateVesselToRetractorAngle(self, vesselVector, retractorVector):
    angleRadians = vtk.vtkMath.AngleBetweenVectors(vesselVector[0:3], retractorVector[0:3])
    angleDegrees = round(vtk.vtkMath.DegreesFromRadians(angleRadians), 2)
    if self.metrics['maxAngle'] < angleDegrees:
      self.metrics['maxAngle'] = angleDegrees
    elif self.metrics['minAngle'] > angleDegrees:
      self.metrics['minAngle'] = angleDegrees
  
  
  def updateTransforms(self, event, caller):
    #self.updateSkeletonModel()
    triggerToCutter = slicer.mrmlScene.GetFirstNodeByName('TriggerToCutter')    
    if triggerToCutter == None:
      logging.error('Could not found TriggerToCutter!')

    triggerToCutterTransform = triggerToCutter.GetTransformToParent()    
    angles = triggerToCutterTransform.GetOrientation()    
    # Todo: Implement cutter angle computation as outlined below    
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
    # save fiducial point every 0.25 seconds 
    if ( time.time() - self.lastTimestamp) > 0.25: 
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
      if self.runTutor and math.fabs(openAngle) < 0.25:
        self.checkModel()
        self.updateDistanceMetrics()


  def checkModel(self): # check if vessel branch needs to be snipped
    minDistance = float("inf")
    index = 0
    a = self.branchStarts
    for point in a:
      cutterTipWorld = [0,0,0,0]
      fiducial = slicer.util.getNode("F")
      fiducial.GetNthFiducialWorldCoordinates(0,cutterTipWorld) # cutterTipWorld now holds the coordinates of 
      distanceToBranch =  self.distance(cutterTipWorld, point) # double check dimensions 
      if distanceToBranch < minDistance:
        minDistance = distanceToBranch
        index = self.branchStarts.index(point) + 1

    
    branchNode = slicer.util.getNode('Model_' + str(index))
    polydata = branchNode.GetPolyData()    
    numVesselPoints = polydata.GetNumberOfPoints()
    vesselPoints = [ self.distance(self.branchStarts[index], polydata.GetPoint(i)) for i in range(numVesselPoints)]
    cutDistance = min(vesselPoints)

    if cutDistance < 250:
      branchDisplayNode = branchNode.GetDisplayNode()
      branchDisplayNode.SetVisibility(False)
     

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
    

  def updateDistanceMetrics(self):
    cutterTipWorld = [0,0,0,0]
    fiducial = slicer.util.getNode("F")
    fiducial.GetNthFiducialWorldCoordinates(0,cutterTipWorld) # cutterTipWorld now holds the coordinates of 
    self.vesselModel = slicer.util.getNode('Model_0') 
    polydata = self.vesselModel.GetPolyData()
    numVesselPoints = polydata.GetNumberOfPoints()
    # TODO check if points need to be reformatted 
    vesselPoints = [ vtkMath.Distance2BetweenPoints(cutterTipWorld, polydata.GetPoint(i)) for i in range(numVesselPoints)]
    cutDistance = min(vesselPoints)
    if self.metrics['maxDistance'] < cutDistance:
      self.metrics['maxDistance'] = str(round(cutDistance, 2)) + " mm"
    if self.metrics['minDistance'] > cutDistance:
      self.metrics['minDistance'] = str(round(cutDistance, 2)) + " mm"
    # TODO average cut distance logic 
    
  
  def getDistanceMetrics(self): 
    if len(self.pathFiducialsX) > 0:
      x = numpy.array(self.pathFiducialsX)
      y = numpy.array(self.pathFiducialsY)
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
    """
    Transforms polydatas and appends them in a single polydata. Sets that up in a MRML model node.
    :return: True on success, False on error
    """

    #self.fiducialsUpdatedSinceLastSave = True ???
    #self.updateScaledAtlasModelsAndPoints() 
    #ScoliUsLib.SpineRegistration.computeRigidTransformsScaledAtlasToRas(self.perVertebraPointsDict_ScaledAtlas, self.perVertebraScaledAtlasToRasTransforms)
    appender = vtk.vtkAppendPolyData()

    for name, poly in self.modelPolydata.iteritems():
      if poly:
        colors = vtk.vtkIntArray()
        colors.SetNumberOfValues(poly.GetNumberOfPoints())
        for i in range(poly.GetNumberOfPoints()):
          colors.SetValue(i, 1)
        poly.GetPointData().SetScalars(colors)
      transformFilter = vtk.vtkTransformPolyDataFilter()
      transformFilter.SetTransform(self.modelPolydata[name])
      transformFilter.SetInputData(poly)
      transformFilter.Update()
      appender.AddInputData(transformFilter.GetOutput())
    appender.Update()
    modelNode = slicer.util.getFirstNodeByName(self.SKELETON_MODEL_NAME)
    if modelNode is None:
      logging.error("Model node not found: {0}".format(self.SKELETON_MODEL_NAME))
      return False
    modelNode.SetAndObservePolyData(appender.GetOutput())  
    return True
    
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

